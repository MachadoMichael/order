from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import hash_password
from app.models import Customer, User, UserRole

CLIENTES = [
    ("Marina Alves", "marina@exemplo.com", "30140071", "Rua dos Aimores", "1200", "Belo Horizonte", "MG"),
    ("Rafael Souza", "rafael@exemplo.com", "01310930", "Avenida Paulista", "900", "Sao Paulo", "SP"),
    ("Juliana Prado", "juliana@exemplo.com", "13015100", "Rua Barao de Jaguara", "300", "Campinas", "SP"),
]


def seed(session: Session) -> dict:
    criados = {"users": 0, "customers": 0}

    if session.exec(select(User).limit(1)).first() is None:
        session.add(
            User(
                email=settings.seed_admin_email,
                password_hash=hash_password(settings.seed_admin_password),
                role=UserRole.ADMIN,
            )
        )
        criados["users"] = 1

    if session.exec(select(Customer).limit(1)).first() is None:
        for name, email, cep, street, number, city, state in CLIENTES:
            session.add(
                Customer(name=name, email=email, cep=cep, street=street,
                         number=number, city=city, state=state)
            )
        criados["customers"] = len(CLIENTES)

    session.commit()
    return criados
