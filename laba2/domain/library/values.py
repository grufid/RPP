from dataclasses import dataclass
from datetime import date
from uuid import UUID

from domain.common.exceptions import InvalidValueObject
from domain.common.values import Money


@dataclass(frozen=True)
class BookId:
    value: UUID
    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise InvalidValueObject("BookId должен быть UUID")


@dataclass(frozen=True)
class CopyId:
    value: UUID
    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise InvalidValueObject("CopyId должен быть UUID")


@dataclass(frozen=True)
class ReaderId:
    value: UUID
    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise InvalidValueObject("ReaderId должен быть UUID")


@dataclass(frozen=True)
class LoanId:
    value: UUID
    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise InvalidValueObject("LoanId должен быть UUID")


@dataclass(frozen=True)
class ISBN:
    """ISBN-10 или ISBN-13 (дефисы допустимы)."""
    value: str

    def __post_init__(self) -> None:
        digits = self.value.replace("-", "").strip()
        if not digits.isdigit() or len(digits) not in (10, 13):
            raise InvalidValueObject(
                f"ISBN должен содержать 10 или 13 цифр, получено: {self.value!r}"
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class FullName:
    """ФИО читателя."""
    first_name: str
    last_name: str
    middle_name: str = ""

    def __post_init__(self) -> None:
        if not self.first_name.strip():
            raise InvalidValueObject("Имя обязательно")
        if not self.last_name.strip():
            raise InvalidValueObject("Фамилия обязательна")

    def __str__(self) -> str:
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)


@dataclass(frozen=True)
class TicketNumber:
    """Номер читательского билета."""
    value: str
    MIN_LENGTH = 4

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise InvalidValueObject("Номер билета обязателен")
        if len(self.value.strip()) < self.MIN_LENGTH:
            raise InvalidValueObject(
                f"Номер билета короче {self.MIN_LENGTH} символов"
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class LoanPeriod:
    issue_date: date
    due_date: date
    return_date: date | None = None

    def __post_init__(self) -> None:
        if self.due_date < self.issue_date:
            raise InvalidValueObject("Срок возврата раньше даты выдачи")
        if self.return_date is not None and self.return_date < self.issue_date:
            raise InvalidValueObject("Дата возврата раньше даты выдачи")

    def is_overdue(self) -> bool:
        return self.return_date is not None and self.return_date > self.due_date

    def overdue_days(self) -> int:
        if not self.is_overdue():
            return 0
        return (self.return_date - self.due_date).days


@dataclass(frozen=True)
class Fine:
    """Штраф за просрочку. Сумма — от дней и ставки."""
    amount: Money
    days_overdue: int = 0

    def __post_init__(self) -> None:
        if self.amount.amount < 0:
            raise InvalidValueObject("Штраф не может быть отрицательным")
        if self.days_overdue < 0:
            raise InvalidValueObject("Дней просрочки не может быть < 0")

    @classmethod
    def for_overdue(cls, days: int, rate_per_day: Money) -> "Fine":
        return cls(amount=rate_per_day * days, days_overdue=days)

    def __str__(self) -> str:
        if self.days_overdue:
            return f"{self.amount} (просрочка {self.days_overdue} дн.)"
        return f"{self.amount} (без просрочки)"