from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from domain.common.values import Money
from domain.library.aggregates import Book, Reader
from domain.library.service import LibraryService
from domain.library.values import FullName, TicketNumber
from domain.parking.aggregates import ParkingSpot
from domain.parking.service import ParkingService
from domain.parking.values import (
    LicensePlate, ParkingPolicy, Tariff, VehicleId,
)
from infra.library_memory import (
    InMemoryBookRepository,
    InMemoryLoanRepository,
    InMemoryReaderRepository,
)
from infra.parking_memory import (
    InMemoryParkingSessionRepository,
    InMemoryParkingSpotRepository,
)


def demo_library() -> None:
    print("=" * 55)
    print("БИБЛИОТЕКА")
    print("=" * 55)

    books = InMemoryBookRepository()
    readers = InMemoryReaderRepository()
    loans = InMemoryLoanRepository()
    service = LibraryService(fine_per_day=Money(Decimal("100")))

    # --- Книга ---
    book = Book.create("Мастер и Маргарита", "М.А. Булгаков", total=1)
    books.save(book)
    print(f"Книга: {book.title} (всего {book.total_copies} экз.)")

    # --- Читатель ---
    reader = Reader.create(
        FullName("Иван", "Иванов", "Иванович"),
        TicketNumber("ЧБ-0001"),
    )
    readers.save(reader)
    print(f"Читатель: {reader.full_name}, билет {reader.ticket_number}")

    today = date.today()

    # --- Выдача ---
    loan = service.issue_book(book, reader, today, loan_days=14)
    loans.save(loan)
    print(f"Выдана. Доступно экземпляров: {book.available_copies}")

    # --- Возврат с просрочкой 5 дней ---
    return_date = today + timedelta(days=19)
    fine = service.return_book(book, loan, return_date)
    loans.save(loan)
    print(f"Возврат. Штраф: {fine}")
    print(f"Доступно экземпляров: {book.available_copies}")

    # --- Нарушение: повторное закрытие ---
    try:
        service.return_book(book, loan, return_date)
    except Exception as e:
        print(f"Инвариант сработал: {e}")

    # --- Выдача сверх наличия ---
    for _ in range(3):
        try:
            l = service.issue_book(book, reader, today)
            loans.save(l)
            print(f"Выдано ещё, осталось: {book.available_copies}")
        except Exception as e:
            print(f"Инвариант сработал: {e}")
            break


def demo_parking() -> None:
    print()
    print("=" * 55)
    print("ПАРКОВКА")
    print("=" * 55)

    spots = InMemoryParkingSpotRepository()
    sessions = InMemoryParkingSessionRepository()
    service = ParkingService()
    tariff = Tariff(hourly_rate=Money(Decimal("100")), minimum_hours=1)
    policy = ParkingPolicy(max_hours=24,
                           overstay_fine=Money(Decimal("1000")))

    spot = ParkingSpot.create("A-01")
    spots.save(spot)

    vehicle = VehicleId(uuid4())
    plate = LicensePlate("А123ВС77")

    # --- Въезд: 2 часа 30 минут назад ---
    entry = datetime.now() - timedelta(hours=2, minutes=30)
    session = service.start_session(
        spot, vehicle, plate, entry,
        active_session_lookup=sessions.find_active_by_vehicle,
    )
    sessions.save(session)
    spots.save(spot)
    print(f"Въезд {plate}. Статус места: {spot.status.value}")

    # --- Попытка въехать той же машиной на ДРУГОЕ место ---
    spot_other = ParkingSpot.create("A-99")
    spots.save(spot_other)
    try:
        service.start_session(
            spot_other, vehicle, plate, datetime.now(),
            active_session_lookup=sessions.find_active_by_vehicle,
        )
    except Exception as e:
        print(f"Инвариант сработал: {e}")

    # --- Выезд: 2 ч 30 мин → 3 часа, 300 RUB ---
    cost = service.end_session(spot, session, datetime.now(),
                               tariff, policy)
    sessions.save(session)
    spots.save(spot)
    print(f"Выезд. К оплате: {cost}. Статус места: {spot.status.value}")

    # --- Попытка закрыть повторно ---
    try:
        service.end_session(spot, session, datetime.now(), tariff, policy)
    except Exception as e:
        print(f"Инвариант сработал: {e}")

    # --- Демонстрация штрафа за превышение 24 часов ---
    spot2 = ParkingSpot.create("B-02")
    spots.save(spot2)
    vehicle2 = VehicleId(uuid4())
    plate2 = LicensePlate("В456ЕК99")
    entry2 = datetime.now() - timedelta(hours=30)
    session2 = service.start_session(
        spot2, vehicle2, plate2, entry2,
        active_session_lookup=sessions.find_active_by_vehicle,
    )
    sessions.save(session2)
    cost2 = service.end_session(spot2, session2, datetime.now(),
                                tariff, policy)
    sessions.save(session2)
    print(f"Превышение 24ч. К оплате: {cost2} "
          f"(включая штраф {session2.overstay_fine})")


if __name__ == "__main__":
    demo_library()
    demo_parking()