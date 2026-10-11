import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from domain.common.exceptions import InvalidValueObject
from domain.common.values import Money


@dataclass(frozen=True)
class SpotId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise InvalidValueObject("SpotId должен быть UUID")


@dataclass(frozen=True)
class VehicleId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise InvalidValueObject("VehicleId должен быть UUID")


@dataclass(frozen=True)
class SessionId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise InvalidValueObject("SessionId должен быть UUID")


@dataclass(frozen=True)
class LicensePlate:
    """Номерной знак автомобиля (российский формат)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise InvalidValueObject("Номерной знак обязателен")
        if not re.match(r"^[А-Я]\d{3}[А-Я]{2}\d{2,3}$", self.value.upper()):
            raise InvalidValueObject(f"Некорректный номер: {self.value}")

    def __str__(self) -> str:
        return self.value.upper()


@dataclass(frozen=True)
class Tariff:
    """Тариф: ставка за час и минимальное время оплаты."""

    hourly_rate: Money
    minimum_hours: int = 1

    def __post_init__(self) -> None:
        if self.hourly_rate.amount <= 0:
            raise InvalidValueObject("Ставка должна быть положительной")
        if self.minimum_hours < 1:
            raise InvalidValueObject("Минимум часов не может быть меньше 1")

    def cost_for(self, hours: int) -> Money:
        return self.hourly_rate * max(hours, self.minimum_hours)


@dataclass(frozen=True)
class ParkingPolicy:
    """
    Политика парковки: максимальное время стоянки и штраф за превышение.
    Применяется при закрытии сессии.
    """

    max_hours: int = 24
    overstay_fine: Money = field(
        default_factory=lambda: Money(Decimal("1000"))
    )

    def __post_init__(self) -> None:
        if self.max_hours < 1:
            raise InvalidValueObject("max_hours должен быть >= 1")

    def is_overstay(self, hours: int) -> bool:
        return hours > self.max_hours


@dataclass(frozen=True)
class TimeInterval:
    """Интервал стоянки: въезд и (опционально) выезд."""

    entry_time: datetime
    exit_time: datetime | None = None

    def __post_init__(self) -> None:
        if self.exit_time is not None and self.exit_time < self.entry_time:
            raise InvalidValueObject("Время выезда раньше времени въезда")

    @property
    def is_closed(self) -> bool:
        return self.exit_time is not None

    def billed_hours(self) -> int:
        """Длительность в часах с округлением до полного часа вверх."""
        if not self.is_closed:
            raise InvalidValueObject("Интервал не закрыт")
        seconds = (self.exit_time - self.entry_time).total_seconds()
        return max(1, int(seconds // 3600) + (1 if seconds % 3600 else 0))