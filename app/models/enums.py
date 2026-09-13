import enum


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"                      # criado, ainda sem reserva confirmada
    CONFIRMED = "CONFIRMED"                  # estoque reservado e frete cotado
    REJECTED_NO_STOCK = "REJECTED_NO_STOCK"  # o estoque negou
    REJECTED_DELIVERY = "REJECTED_DELIVERY"  # a cotacao falhou, reserva compensada
    CANCELLED = "CANCELLED"                  # cancelado, reserva liberada
