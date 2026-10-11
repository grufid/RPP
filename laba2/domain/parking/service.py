from datetime import datetime
from typing import Callable, Optional

from domain.common.exceptions import DomainInvariantViolation
from domain.common.values import Money
from domain.parking.aggregates import ParkingSession, ParkingSpot
from domain.parking.values import (
    LicensePlate, ParkingPolicy, Tariff, VehicleId,
)

ActiveSessionLookup = Callable[[VehicleId], Optional[ParkingSession]]


class ParkingService:
    """
    Доменный сервис парковки.
    Координирует операции, затрагивающие два агрегата:
    ParkingSpot и ParkingSession.
    """

    def start_session(
        self,
        spot: ParkingSpot,
        vehicle_id: VehicleId,
        license_plate: LicensePlate,
        entry_time: datetime,
        active_session_lookup: ActiveSessionLookup | None = None,
    ) -> ParkingSession:
        """
        Въезд на парковку.

        Если передан active_session_lookup, проверяем, что у машины
        нет другой активной сессии (одна машина — одна парковка).
        """
        if active_session_lookup is not None:
            existing = active_session_lookup(vehicle_id)
            if existing is not None and existing.is_active():
                raise DomainInvariantViolation(
                    f"Машина {license_plate} уже находится на парковке"
                )

        session = ParkingSession.create(
            spot.spot_id, vehicle_id, license_plate, entry_time,
        )
        spot.occupy(session.session_id)
        return session

    def end_session(
        self,
        spot: ParkingSpot,
        session: ParkingSession,
        exit_time: datetime,
        tariff: Tariff,
        policy: ParkingPolicy | None = None,
    ) -> Money:
        """
        Выезд с парковки.
        Возвращает итог к оплате (стоимость + штраф, если был).
        """
        if not session.is_active():
            raise DomainInvariantViolation("Сессия уже закрыта")
        if session.spot_id != spot.spot_id:
            raise DomainInvariantViolation("Сессия не соответствует месту")

        session.close(exit_time, tariff, policy)
        spot.release()
        return session.total_due