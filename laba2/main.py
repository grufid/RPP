from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from domain.common.values import Money
from domain.library.aggregates import Book, Reader
from domain.library.service import LibraryService
from domain.library.values import FullName, ISBN, TicketNumber
from domain.parking.service import ParkingService
from domain.parking.values import (
    LicensePlate, ParkingPolicy, Tariff, VehicleId,
)
from infra.library_memory import (
    InMemoryBookRepository, InMemoryLoanRepository,
    InMemoryReaderRepository,
)
from infra.parking_memory import (
    InMemoryParkingSessionRepository, InMemoryParkingSpotRepository,
)


def demo_library() -> None:
    print("БИБЛИОТЕКА")

    books = InMemoryBookRepository()
    readers = InMemoryReaderRepository()
    loans = InMemoryLoanRepository()
    service = LibraryService(
        books=books, readers=readers, loans=loans,
        fine_per_day=Money(Decimal("100")),
    )

    book = Book.create("Мастер и Маргарита", "М.А. Булгаков",
                       ISBN("978-5-04-116543-3"))
    book.add_copy()
    book.add_copy()
    book.add_copy()
    books.save(book)
    print(f"Книга: {book.title} (всего {book.total_count()} экз.)")

    reader = Reader.create(
        FullName("Иван", "Иванов", "Иванович"),
        TicketNumber("ЧБ-0001"),
    )
    readers.save(reader)
    print(f"Читатель: {reader.full_name} (билет {reader.ticket_number})")

    copy_id = book.copies()[0].id
    loan = service.issue_book(book.book_id, copy_id, reader.reader_id,
                              date.today(), loan_days=14)
    print(f"Выдано. Доступно: {book.available_count()}")

    return_date = date.today() + timedelta(days=19)
    fine = service.return_book(loan.loan_id, return_date)
    print(f"Возврат. Штраф: {fine}")
    print(f"Доступно после возврата: {book.available_count()}")

    try:
        service.return_book(loan.loan_id, return_date)
    except Exception as e:
        print(f"Инвариант сработал: {e}")

    for _ in range(3):
        free = [c for c in book.copies() if not c.on_loan]
        if not free:
            print(f"Инвариант сработал: нет свободных экземпляров")
            break
        try:
            service.issue_book(book.book_id, free[0].id,
                               reader.reader_id, date.today())
            print(f"Выдано ещё, осталось: {book.available_count()}")
        except Exception as e:
            print(f"Инвариант сработал: {e}")
            break


def demo_parking() -> None:
    print()
    print("ПАРКОВКА")
    from domain.parking.aggregates import ParkingSpot

    spots = InMemoryParkingSpotRepository()
    sessions = InMemoryParkingSessionRepository()
    service = ParkingService(spots=spots, sessions=sessions)
    tariff = Tariff(hourly_rate=Money(Decimal("100")), minimum_hours=1)
    policy = ParkingPolicy(max_hours=24,
                           overstay_fine=Money(Decimal("1000")))

    spot = ParkingSpot.create("A-01")
    spots.save(spot)

    vehicle = VehicleId(uuid4())
    plate = LicensePlate("А123ВС77")

    entry = datetime.now() - timedelta(hours=2, minutes=30)
    session = service.start_session(spot.spot_id, vehicle, plate, entry)
    print(f"Въезд {plate}. Статус места: {spot.status.value}")

    other = ParkingSpot.create("A-99")
    spots.save(other)
    try:
        service.start_session(other.spot_id, vehicle, plate, datetime.now())
    except Exception as e:
        print(f"Инвариант сработал: {e}")

    cost = service.end_session(session.session_id, datetime.now(),
                               tariff, policy)
    print(f"Выезд. К оплате: {cost}. Статус места: {spot.status.value}")

    try:
        service.end_session(session.session_id, datetime.now(), tariff, policy)
    except Exception as e:
        print(f"Инвариант сработал: {e}")

    spot2 = ParkingSpot.create("B-02")
    spots.save(spot2)
    vehicle2 = VehicleId(uuid4())
    plate2 = LicensePlate("В456ЕК99")
    entry2 = datetime.now() - timedelta(hours=30)
    session2 = service.start_session(spot2.spot_id, vehicle2, plate2, entry2)
    cost2 = service.end_session(session2.session_id, datetime.now(),
                                tariff, policy)
    print(f"Превышение 24ч. К оплате: {cost2} "
          f"(включая штраф {session2.overstay_fine})")


if __name__ == "__main__":
    demo_library()
    demo_parking()