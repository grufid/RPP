from typing import Optional, Protocol
from uuid import UUID

from domain.parking.aggregates import ParkingSession, ParkingSpot
from domain.parking.values import SessionId, SpotId, VehicleId


class ParkingSpotRepository(Protocol):
    def save(self, spot: ParkingSpot) -> None: ...
    def get(self, spot_id: SpotId) -> Optional[ParkingSpot]: ...


class ParkingSessionRepository(Protocol):
    def save(self, session: ParkingSession) -> None: ...
    def get(self, session_id: SessionId) -> Optional[ParkingSession]: ...
    def find_active_by_vehicle(
        self, vehicle_id: VehicleId
    ) -> Optional[ParkingSession]: ...


class InMemoryParkingSpotRepository:
    def __init__(self) -> None:
        self._storage: dict[UUID, ParkingSpot] = {}

    def save(self, spot: ParkingSpot) -> None:
        self._storage[spot.spot_id.value] = spot

    def get(self, spot_id: SpotId) -> Optional[ParkingSpot]:
        return self._storage.get(spot_id.value)


class InMemoryParkingSessionRepository:
    def __init__(self) -> None:
        self._storage: dict[UUID, ParkingSession] = {}

    def save(self, session: ParkingSession) -> None:
        self._storage[session.session_id.value] = session

    def get(self, session_id: SessionId) -> Optional[ParkingSession]:
        return self._storage.get(session_id.value)

    def find_active_by_vehicle(
        self, vehicle_id: VehicleId
    ) -> Optional[ParkingSession]:
        for session in self._storage.values():
            if (session.vehicle_id == vehicle_id
                    and session.is_active()):
                return session
        return None