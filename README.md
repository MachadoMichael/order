# orders-api — API principal

API de **pedidos** de uma loja. É a única porta de entrada do cliente e não é dona
nem do estoque nem do cálculo de frete: ela **orquestra** dois serviços autônomos
que sabem fazer isso e devolve ao cliente uma resposta única e consolidada.

O problema que resolve: registrar um pedido sem vender o que não existe e sem
prometer um frete que nunca foi calculado.

Este é o **módulo principal** do MVP. Os outros dois estão em repositórios separados:

| Módulo | Repositório | Porta |
|---|---|---|
| **orders-api** (este) | https://github.com/MachadoMichael/order | 8000 |
| inventory-service | https://github.com/MachadoMichael/inventory | 8001 |
| delivery-service | https://github.com/MachadoMichael/delivery | 8002 |

---

## Arquitetura

![Arquitetura do MVP](docs/arquitetura.png)

Três serviços próprios, dois bancos separados e duas APIs externas. Cada serviço é
dono dos seus dados: **o pedido nunca dá `JOIN` no estoque, ele pergunta por HTTP.**

| Componente | Papel | Responsabilidade exclusiva |
|---|---|---|
| `orders-api` | Principal | Autentica, valida, orquestra, persiste o pedido e responde |
| `inventory-service` | Secundária | Dono do saldo: reserva, libera e consome estoque |
| `delivery-service` | Secundária | Stateless: distância, frete e prazo |
| ViaCEP | Externa | CEP → logradouro, município, UF |
| Nominatim | Externa | Município → latitude e longitude |

### O fluxo de `POST /orders`

![Fluxo do pedido](docs/fluxo-pedido.png)

1. Busca **preço e peso** de cada SKU no `inventory-service` e congela o preço no item
2. **Reserva o saldo** — o estoque é um portão: se negar, para aqui e a entrega nunca é consultada
3. **Cotiza o frete** no `delivery-service`
4. Se a cotação falhar, **libera a reserva** e devolve 503

O passo 4 é uma **transação compensatória**. Os dois serviços têm bancos separados,
então não existe *rollback* distribuído — existe compensação explícita.

### Estratégias de comunicação

| Estratégia | Como aparece |
|---|---|
| Orquestração com portão | A entrega só é chamada se o estoque aprovar. Falhar cedo evita trabalho inútil |
| Transação compensatória | Cotação falhou → `DELETE /reservations/{id}` devolve o saldo |
| Idempotência | `POST /reservations` é único por `order_id`: o retry não reserva duas vezes |
| Timeout e retry | 3s por chamada, 1 retry com backoff — **apenas** em falha de transporte ou 5xx |
| Circuit breaker | 3 falhas seguidas abrem o circuito por 20s, por dependência |
| Rastreabilidade | `X-Correlation-ID` gerado aqui e propagado aos dois serviços |

Um `409` do estoque é **resposta de negócio**, não falha: não há retry nem
penalidade no breaker.

---

## APIs externas utilizadas

Consumidas exclusivamente pelo `delivery-service`. Nenhuma exige cadastro ou
chave de API.

| API | URL | Uso | Cadastro | Licença |
|---|---|---|---|---|
| **ViaCEP** | https://viacep.com.br | CEP → endereço | Não exige | Uso livre e gratuito |
| **Nominatim (OpenStreetMap)** | https://nominatim.openstreetmap.org | Município → coordenadas | Não exige | Dados sob **ODbL**; uso sujeito à [política do OSM](https://operations.osmfoundation.org/policies/nominatim/) |

### Rotas consumidas

| API | Rota | Para quê |
|---|---|---|
| ViaCEP | `GET /ws/{cep}/json/` | Logradouro, bairro, município e UF |
| Nominatim | `GET /search?city=&state=&country=Brazil&format=jsonv2` | Latitude e longitude do município |
| Nominatim | `GET /status.php?format=json` | Health check |

### Os dados externos são tratados, nunca repassados

Nenhuma resposta das externas chega ao cliente como veio, e **em nenhum momento
há redirecionamento** para outra aplicação:

- A ViaCEP devolve 13 campos (`logradouro`, `localidade`, `uf`, `ibge`, `gia`, `siafi`…);
  o `delivery-service` devolve 5, no nosso próprio schema (`street`, `city`, `state`…).
- A **distância é calculada no nosso código**, pela fórmula de Haversine sobre as
  coordenadas, e vira faixa de zona, preço e prazo.

Conformidade com a política do Nominatim: `User-Agent` identificável, no máximo
1 requisição por segundo e cache em memória com TTL de 24h.

> **Simplificação assumida:** Haversine dá a distância em **linha reta**. O campo
> `distance_km` aplica um fator de correção de 1,3 para aproximar a rodoviária, e o
> `straight_line_km` original vai junto na resposta para que ninguém confunda um com
> o outro. Não há motor de roteirização.

---

## Como executar

### Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e Docker Compose
- Portas livres: `8000`, `8001`, `8002` e `5432`

### Passo a passo

O `docker-compose.yml` deste repositório sobe **os três serviços e o banco**. Para
isso ele precisa do código das duas secundárias, então clone os três repositórios
**como irmãos**:

```bash
mkdir mvp && cd mvp
git clone https://github.com/MachadoMichael/order.git      order
git clone https://github.com/MachadoMichael/inventory.git  inventory
git clone https://github.com/MachadoMichael/delivery.git   delivery
```

A estrutura esperada é esta:

```
mvp/
├── order/       <- este repositório, contém o docker-compose.yml
├── inventory/
└── delivery/
```

Se você clonou com outros nomes de pasta, não precisa editar o compose — basta
apontar os caminhos:

```bash
export INVENTORY_PATH=../meu-inventory
export DELIVERY_PATH=../meu-delivery
```

Depois é só subir:

```bash
cd order
docker compose up --build
```

Na primeira execução o banco é criado e populado automaticamente com um catálogo
de 8 produtos, 3 clientes e um usuário administrador.

### Acessos

| Serviço | Swagger | Health |
|---|---|---|
| orders-api | http://localhost:8000/docs | http://localhost:8000/health |
| inventory-service | http://localhost:8001/docs | http://localhost:8001/health |
| delivery-service | http://localhost:8002/docs | http://localhost:8002/health |

**Credenciais do seed:** `admin@loja.com` / `admin123`

No Swagger, clique em **Authorize** e informe esse email no campo `username`.

### Parar

```bash
docker compose down          # para os containers
docker compose down -v       # também apaga os dados do banco
```

### Se algo der errado

O schema do banco é criado na subida, pelo `create_all` do SQLModel — este projeto
não usa ferramenta de migração. Isso tem uma consequência prática: **se você alterar
um modelo depois de já ter subido a stack, o banco existente não é atualizado.** Um
`ENUM` novo, por exemplo, causa `invalid input value for enum`.

A solução é recriar o volume, que é exatamente o que um clone novo faz:

```bash
docker compose down -v && docker compose up --build
```

---

## Rotas

Todas as rotas exigem `Authorization: Bearer <token>`, exceto `/health`,
`/auth/register` e `/auth/login`.

### Autenticação

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/auth/register` | Cria um usuário |
| `POST` | `/auth/login` | Devolve o JWT |
| `GET` | `/auth/me` | Usuário do token atual |

### Clientes

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/customers` | Lista paginada, com `?state=`, `?search=`, `?sort=`, `?order=` |
| `GET` | `/customers/{id}` | Detalha um cliente |
| `POST` | `/customers` | Cadastra um cliente |
| `PUT` | `/customers/{id}` | Atualiza um cliente |
| `DELETE` | `/customers/{id}` | Remove um cliente |

### Pedidos

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/orders` | Lista paginada, com `?status=`, `?customer_id=`, `?created_from=`, `?created_to=` |
| `GET` | `/orders/{id}` | Detalha um pedido |
| `POST` | `/orders` | **Orquestra estoque e entrega** |
| `PUT` | `/orders/{id}/delivery` | Troca o CEP e recotiza o frete |
| `DELETE` | `/orders/{id}` | Cancela e devolve o saldo ao estoque |

### Infra

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Serviço, banco e estado do circuit breaker de cada dependência |

### Estados do pedido

| Status | Significado |
|---|---|
| `PENDING` | Criado, aguardando a reserva |
| `CONFIRMED` | Estoque reservado e frete cotado |
| `REJECTED_NO_STOCK` | O estoque negou — a entrega nunca foi chamada |
| `REJECTED_DELIVERY` | A cotação falhou e a reserva foi compensada |
| `CANCELLED` | Cancelado pelo usuário, saldo devolvido |

### Erros

Toda falha devolve JSON com código estável, nunca *stacktrace*:

```json
{
  "code": "OUT_OF_STOCK",
  "message": "estoque insuficiente: SKU-2071 (pedido 99, disponivel 7)",
  "details": [
    { "sku": "SKU-2071", "requested": 99, "available": 7 },
    { "order_id": "54b6be30-...", "status": "REJECTED_NO_STOCK" }
  ]
}
```

| Código | HTTP | Quando |
|---|---|---|
| `INVALID_CREDENTIALS` | 401 | Email ou senha errados |
| `CUSTOMER_NOT_FOUND` / `ORDER_NOT_FOUND` | 404 | Recurso inexistente |
| `PRODUCT_UNAVAILABLE` | 404 | SKU fora do catálogo |
| `OUT_OF_STOCK` | 409 | Saldo insuficiente, com a lista de faltas |
| `INVALID_ORDER_STATE` | 409 | Operação incompatível com o status |
| `EMAIL_ALREADY_USED` | 409 | Email já cadastrado |
| `DEPENDENCY_UNAVAILABLE` | 503 | Estoque ou entrega fora do ar |

---

## Testando o fluxo completo

```bash
# 1. Login
TOKEN=$(curl -s -X POST localhost:8000/auth/login \
  -d 'username=admin@loja.com&password=admin123' | jq -r .access_token)

# 2. Pegue um cliente do seed
CID=$(curl -s localhost:8000/customers -H "Authorization: Bearer $TOKEN" \
  | jq -r '.items[0].id')

# 3. Pedido feliz
curl -X POST localhost:8000/orders -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"customer_id\":\"$CID\",\"items\":[{\"sku\":\"SKU-1042\",\"quantity\":2}]}"
#   -> 201 CONFIRMED, com reservation_id, frete e prazo

# 4. O portão do estoque
curl -X POST localhost:8000/orders -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"customer_id\":\"$CID\",\"items\":[{\"sku\":\"SKU-2071\",\"quantity\":9999}]}"
#   -> 409 OUT_OF_STOCK, e a entrega nunca foi chamada

# 5. A COMPENSAÇÃO
curl -s localhost:8001/products/SKU-1042 | jq .quantity_available   # anote
docker compose stop delivery-service
curl -X POST localhost:8000/orders -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"customer_id\":\"$CID\",\"items\":[{\"sku\":\"SKU-1042\",\"quantity\":10}]}"
#   -> 503 tratado, pedido em REJECTED_DELIVERY
curl -s localhost:8001/products/SKU-1042 | jq .quantity_available   # idêntico
#   -> a reserva foi criada e depois liberada: o saldo voltou
docker compose start delivery-service
```

---

## Variáveis de ambiente

Veja `.env.example`. Todas têm padrão sensato no `docker-compose.yml`.

| Variável | Padrão | Para quê |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://mvp:mvp@postgres:5432/orders_db` | Conexão com o banco |
| `INVENTORY_BASE_URL` | `http://inventory-service:8001` | Onde está o estoque |
| `DELIVERY_BASE_URL` | `http://delivery-service:8002` | Onde está a entrega |
| `JWT_SECRET` | `troque-em-producao` | Assinatura do token |
| `JWT_EXPIRE_MINUTES` | `60` | Validade do token |
| `HTTP_TIMEOUT_SECONDS` | `3.0` | Timeout das chamadas entre serviços |
| `HTTP_MAX_ATTEMPTS` | `2` | 1 tentativa + 1 retry |
| `BREAKER_FAILURE_THRESHOLD` | `3` | Falhas seguidas para abrir o circuito |
| `BREAKER_RESET_SECONDS` | `20` | Quanto tempo o circuito fica aberto |

---

## Estrutura do projeto

```
order/
├── docker-compose.yml        sobe os 3 serviços + Postgres
├── Dockerfile
├── docker/init-db.sql        cria orders_db e inventory_db
├── docs/                     diagramas
└── app/
    ├── main.py
    ├── database.py           engine, sessão e criação do schema
    ├── seed.py               usuário admin e clientes iniciais
    ├── core/                 config, security (JWT), correlation, logging,
    │                         http_client (retry + breaker), exceptions,
    │                         responses (Page[T], ErrorResponse)
    ├── models/               User, Customer, Order, OrderItem
    ├── repositories/         acesso a dados: paginação, filtros, ordenação
    ├── clients/              adaptadores HTTP para o estoque e a entrega
    ├── services/             regra de negócio: orchestrator, auth, clientes
    └── routers/              auth, customers, orders, health
```

`clients/` guarda os adaptadores para **outros serviços**; `services/` fica só com
regra de negócio deste serviço. A mesma separação existe no `delivery`, onde
`clients/` fala com ViaCEP e Nominatim.

Cada arquivo de `models/` traz a tabela **e** o contrato HTTP correspondente —
`CustomerBase`, `Customer` (a tabela), `CustomerCreate`, `CustomerPublic`. É o
padrão do SQLModel: um campo declarado uma vez só, servindo de ORM, validação e
schema do Swagger. Não existe pasta `schemas/` separada porque ela reintroduziria
a duplicação que o SQLModel existe para eliminar.

## Stack

Python 3.12 · FastAPI · SQLModel · PostgreSQL 16 · httpx · PyJWT · bcrypt · Docker
