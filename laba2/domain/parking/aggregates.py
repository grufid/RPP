from datetime import datetime
from enum import Enum
from uuid import uuid4

from domain.common.exceptions import DomainInvariantViolation
from domain.common.values import Money
from domain.parking.values import (
    LicensePlate, ParkingPolicy, SessionId, SpotId, Tariff,
    TimeInterval, VehicleId,
)


class SpotStatus(Enum):
    FREE = "свободно"
    OCCUPIED = "занято"


class SessionStatus(Enum):
    ACTIVE = "активна"
    CLOSED = "закрыта"


class ParkingSpot:
    """
    Агрегат-корень «Парковочное место».

    Инварианты:
      - место не может быть занято повторно (occupy);
      - нельзя освободить свободное место (release).

    Статус — вычисляемое свойство на основе active_session_id,
    поэтому некорректное состояние физически невозможно.
    """

    def __init__(self, spot_id: SpotId, number: str,
                 active_session_id: SessionId | None = None) -> None:
        self._spot_id = spot_id
        self._number = number
        self._active_session_id = active_session_id

    @property
    def spot_id(self) -> SpotId:
        return self._spot_id

    @property
    def number(self) -> str:
        return self._number

    @property
    def active_session_id(self) -> SessionId | None:
        return self._active_session_id

    @property
    def status(self) -> SpotStatus:
        return (SpotStatus.OCCUPIED if self._active_session_id is not None
                else SpotStatus.FREE)

    def is_free(self) -> bool:
        return self._active_session_id is None

    @classmethod
    def create(cls, number: str) -> "ParkingSpot":
        return cls(SpotId(uuid4()), number)

    @classmethod
    def restore(cls, spot_id: SpotId, number: str,
                active_session_id: SessionId | None) -> "ParkingSpot":
        return cls(spot_id, number, active_session_id)

    def occupy(self, session_id: SessionId) -> None:
        if self._active_session_id is not None:
            raise DomainInvariantViolation(
                f"Место {self._number} уже занято"
            )
        self._active_session_id = session_id

    def release(self) -> None:
        if self._active_session_id is None:
            raise DomainInvariantViolation(
                f"Место {self._number} не занято"
            )
        self._active_session_id = None


class ParkingSession:
    """
    Агрегат-корень «Парковочная сессия».

    Связь с ParkingSpot — по spot_id (не объект).
    Связь с Vehicle — по vehicle_id (не объект).
    Номер машины хранится как VO LicensePlate.

    Инварианты:
      - сессию нельзя закрыть дважды;
      - время выезда не раньше времени въезда;
      - стоимость рассчитывается по тарифу;
      - при превышении max_hours добавляется штраф (если передана политика).
    """

    def __init__(self, session_id: SessionId, spot_id: SpotId,
                 vehicle_id: VehicleId, license_plate: LicensePlate,
                 interval: TimeInterval,
                 status: SessionStatus = SessionStatus.ACTIVE,
                 cost: Money | None = None,
                 overstay_fine: Money | None = None) -> None:
        self._session_id = session_id
        self._spot_id = spot_id
        self._vehicle_id = vehicle_id
        self._license_plate = license_plate
        self._interval = interval
        self._status = status
        self._cost = cost
        self._overstay_fine = overstay_fine
        self._check_invariants()

    def _check_invariants(self) -> None:
        if self._status is SessionStatus.CLOSED:
            if not self._interval.is_closed:
                raise DomainInvariantViolation(
                    "Закрытая сессия без времени выезда"
                )
            if self._cost is None:
                raise DomainInvariantViolation(
                    "Закрытая сессия без рассчитанной стоимости"
                )
        if self._status is SessionStatus.ACTIVE and self._interval.is_closed:
            raise DomainInvariantViolation(
                "Активная сессия не может иметь времени выезда"
            )

    @property
    def session_id(self) -> SessionId:
        return self._session_id

    @property
    def spot_id(self) -> SpotId:
        return self._spot_id

    @property
    def vehicle_id(self) -> VehicleId:
        return self._vehicle_id

    @property
    def license_plate(self) -> LicensePlate:
        return self._license_plate

    @property
    def interval(self) -> TimeInterval:
        return self._interval

    @property
    def status(self) -> SessionStatus:
        return self._status

    @property
    def cost(self) -> Money | None:
        return self._cost

    @property
    def overstay_fine(self) -> Money | None:
        return self._overstay_fine

    @property
    def total_due(self) -> Money | None:
        """Итог к оплате: стоимость + штраф за превышение."""
        if self._cost is None:
            return None
        if self._overstay_fine is None:
            return self._cost
        return self._cost + self._overstay_fine

    @classmethod
    def create(cls, spot_id: SpotId, vehicle_id: VehicleId,
               license_plate: LicensePlate,
               entry_time: datetime) -> "ParkingSession":
        return cls(
            session_id=SessionId(uuid4()),
            spot_id=spot_id,
            vehicle_id=vehicle_id,
            license_plate=license_plate,
            interval=TimeInterval(entry_time=entry_time),
        )

    @classmethod
    def restore(cls, session_id: SessionId, spot_id: SpotId,
                vehicle_id: VehicleId, license_plate: LicensePlate,
                interval: TimeInterval, status: SessionStatus,
                cost: Money | None = None,
                overstay_fine: Money | None = None) -> "ParkingSession":
        return cls(session_id, spot_id, vehicle_id, license_plate,
                   interval, status, cost, overstay_fine)

    def is_active(self) -> bool:
        return self._status is SessionStatus.ACTIVE

    def close(self, exit_time: datetime, tariff: Tariff,
              policy: ParkingPolicy | None = None) -> Money:
        if self._status is SessionStatus.CLOSED:
            raise DomainInvariantViolation("Сессия уже закрыта")
        if exit_time < self._interval.entry_time:
            raise DomainInvariantViolation(
                "Время выезда раньше времени въезда"
            )

        self._interval = TimeInterval(self._interval.entry_time, exit_time)
        hours = self._interval.billed_hours()
        self._cost = tariff.cost_for(hours)

        if policy is not None and policy.is_overstay(hours):
            self._overstay_fine = policy.overstay_fine
        else:
            self._overstay_fine = Money(self._cost.amount * 0)  # 0 RUB

        self._status = SessionStatus.CLOSED
        return self._cost