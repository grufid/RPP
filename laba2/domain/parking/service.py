from datetime import datetime

from domain.common.exceptions import DomainInvariantViolation
from domain.common.values import Money
from domain.parking.aggregates import ParkingSession
from domain.parking.repositories import (
    ParkingSessionRepository, ParkingSpotRepository,
)
from domain.parking.values import (
    LicensePlate, ParkingPolicy, SessionId, SpotId, Tariff, VehicleId,
)


class ParkingService:
    """
    Доменный сервис парковки.
    Координирует операции, затрагивающие ParkingSpot и ParkingSession.
    """

    def __init__(self, spots: ParkingSpotRepository,
                 sessions: ParkingSessionRepository) -> None:
        self._spots = spots
        self._sessions = sessions

    def start_session(self, spot_id: SpotId, vehicle_id: VehicleId,
                      license_plate: LicensePlate,
                      entry_time: datetime) -> ParkingSession:
        existing = self._sessions.find_active_by_vehicle(vehicle_id)
        if existing is not None and existing.is_active():
            raise DomainInvariantViolation(
                f"Машина {license_plate} уже находится на парковке"
            )

        spot = self._spots.get(spot_id)
        session = ParkingSession.create(spot.spot_id, vehicle_id,
                                        license_plate, entry_time)
        spot.occupy(session.session_id)

        self._spots.save(spot)
        self._sessions.save(session)
        return session

    def end_session(self, session_id: SessionId, exit_time: datetime,
                    tariff: Tariff,
                    policy: ParkingPolicy | None = None) -> Money:
        session = self._sessions.get(session_id)
        if not session.is_active():
            raise DomainInvariantViolation("Сессия уже закрыта")

        spot = self._spots.get(session.spot_id)
        session.close(exit_time, tariff, policy)
        spot.release()

        self._sessions.save(session)
        self._spots.save(spot)
        return session.total_due