from dataclasses import dataclass
from decimal import Decimal

from domain.common.exceptions import InvalidValueObject


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "RUB"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise InvalidValueObject("Сумма не может быть отрицательной")
        if not self.currency or len(self.currency) != 3:
            raise InvalidValueObject("Валюта — трёхбуквенный код")

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise InvalidValueObject("Нельзя складывать разные валюты")
        return Money(self.amount + other.amount, self.currency)

    def __mul__(self, k: int) -> "Money":
        if k < 0:
            raise InvalidValueObject("Множитель не может быть отрицательным")
        return Money(self.amount * k, self.currency)

    @classmethod
    def zero(cls, currency: str = "RUB") -> "Money":
        return cls(Decimal("0"), currency)

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"