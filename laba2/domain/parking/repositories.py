from typing import Optional, Protocol

from domain.parking.aggregates import ParkingSession, ParkingSpot
from domain.parking.values import SessionId, SpotId, VehicleId


class ParkingSpotRepository(Protocol):
    def get(self, spot_id: SpotId) -> ParkingSpot: ...
    def save(self, spot: ParkingSpot) -> None: ...


class ParkingSessionRepository(Protocol):
    def get(self, session_id: SessionId) -> ParkingSession: ...
    def save(self, session: ParkingSession) -> None: ...
    def find_active_by_vehicle(
        self, vehicle_id: VehicleId
    ) -> Optional[ParkingSession]: ...