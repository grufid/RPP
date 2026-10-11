"""Полная проверка инвариантов лабораторной работы №2."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from domain.common.exceptions import (
    DomainInvariantViolation, InvalidValueObject,
)
from domain.common.values import Money
from domain.library.aggregates import Book, Loan, LoanStatus, Reader
from domain.library.service import LibraryService
from domain.library.values import (
    BookCopy, Fine, FullName, LoanPeriod, ReaderId, TicketNumber,
)
from domain.parking.aggregates import (
    ParkingSession, ParkingSpot, SessionStatus, SpotStatus,
)
from domain.parking.service import ParkingService
from domain.parking.values import (
    LicensePlate, ParkingPolicy, Tariff, TimeInterval, VehicleId,
)
from infra.parking_memory import InMemoryParkingSessionRepository

PASSED = 0
FAILED = 0


def check(description: str, condition: bool) -> None:
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  [OK]   {description}")
    else:
        FAILED += 1
        print(f"  [FAIL] {description}")


def expect_error(description: str, exc_type, func) -> None:
    """Проверяет, что func() бросает исключение нужного типа."""
    try:
        func()
    except exc_type:
        check(description, True)
    except Exception as e:
        check(f"{description} (получено {type(e).__name__}: {e})", False)
    else:
        check(f"{description} (исключение не брошено)", False)


def no_error(description: str, func):
    try:
        return func()
    except Exception as e:
        check(f"{description} (неожиданно: {type(e).__name__}: {e})", False)
        return None


# ---------- Общие VO ----------
def test_value_objects() -> None:
    print("\n--- Общие объекты-значения ---")

    # --- Money ---
    expect_error("Money: отрицательная сумма",
                 InvalidValueObject, lambda: Money(Decimal("-1")))
    expect_error("Money: плохая валюта",
                 InvalidValueObject, lambda: Money(Decimal("10"), "RU"))
    check("Money: сложение одинаковых валют",
          Money(Decimal("5")) + Money(Decimal("7")) == Money(Decimal("12")))
    expect_error("Money: сложение разных валют",
                 InvalidValueObject,
                 lambda: Money(Decimal("5")) + Money(Decimal("5"), "USD"))
    check("Money: умножение",
          Money(Decimal("100")) * 5 == Money(Decimal("500")))

    # --- LoanPeriod ---
    expect_error("LoanPeriod: due < issue",
                 InvalidValueObject,
                 lambda: LoanPeriod(date(2026, 1, 10), date(2026, 1, 1)))
    expect_error("LoanPeriod: return < issue",
                 InvalidValueObject,
                 lambda: LoanPeriod(date(2026, 1, 10), date(2026, 1, 20),
                                    date(2026, 1, 5)))
    check("LoanPeriod: не просрочено",
          not LoanPeriod(date(2026, 1, 1), date(2026, 1, 14),
                         date(2026, 1, 10)).is_overdue())
    check("LoanPeriod: 5 дней просрочки",
          LoanPeriod(date(2026, 1, 1), date(2026, 1, 14),
                     date(2026, 1, 19)).overdue_days() == 5)

    # --- TimeInterval ---
    expect_error("TimeInterval: exit < entry",
                 InvalidValueObject,
                 lambda: TimeInterval(datetime(2026, 1, 1, 12),
                                      datetime(2026, 1, 1, 10)))
    check("TimeInterval: 2ч30мин → 3 часа",
          TimeInterval(datetime(2026, 1, 1, 10),
                       datetime(2026, 1, 1, 12, 30)).billed_hours() == 3)
    check("TimeInterval: ровно 2 часа → 2",
          TimeInterval(datetime(2026, 1, 1, 10),
                       datetime(2026, 1, 1, 12)).billed_hours() == 2)
    check("TimeInterval: 10 секунд → 1 час (минимум)",
          TimeInterval(datetime(2026, 1, 1, 10, 0, 0),
                       datetime(2026, 1, 1, 10, 0, 10)).billed_hours() == 1)
    expect_error("TimeInterval: часов у незакрытого интервала",
                 InvalidValueObject,
                 lambda: TimeInterval(datetime(2026, 1, 1)).billed_hours())

    # --- Tariff ---
    expect_error("Tariff: отрицательная ставка",
                 InvalidValueObject,
                 lambda: Tariff(Money(Decimal("-100"))))

    # --- LicensePlate ---
    expect_error("LicensePlate: пустой",
                 InvalidValueObject, lambda: LicensePlate(""))
    expect_error("LicensePlate: неверный формат",
                 InvalidValueObject, lambda: LicensePlate("XXX"))
    no_error("LicensePlate: корректный",
             lambda: LicensePlate("А123ВС77"))

    # --- ParkingPolicy ---
    policy = ParkingPolicy(max_hours=24,
                           overstay_fine=Money(Decimal("1000")))
    check("ParkingPolicy: 30ч > 24 → True", policy.is_overstay(30))
    check("ParkingPolicy: 10ч < 24 → False", not policy.is_overstay(10))
    expect_error("ParkingPolicy: max_hours < 1",
                 InvalidValueObject,
                 lambda: ParkingPolicy(max_hours=0))


# ---------- Book ----------
def test_book() -> None:
    print("\n--- Book (инварианты 1, 2) ---")
    expect_error("total = 0 запрещён",
                 DomainInvariantViolation,
                 lambda: Book.create("X", "Y", 0))
    expect_error("available > total запрещён",
                 DomainInvariantViolation,
                 lambda: Book.restore(
                     Book.create("X", "Y", 2).book_id, "X", "Y", 2, 5))

    book = Book.create("Тест", "Автор", 2)
    check("начально available = total", book.available_copies == 2)
    check("VO BookCopy корректен",
          book.copy == BookCopy(book.book_id, 2))

    book.issue_copy()
    check("после выдачи available = 1", book.available_copies == 1)
    book.issue_copy()
    check("после двух выдач available = 0", book.available_copies == 0)
    expect_error("третья выдача невозможна",
                 DomainInvariantViolation, book.issue_copy)

    book.return_copy()
    check("возврат увеличивает счётчик", book.available_copies == 1)
    book.return_copy()
    check("available = total после двух возвратов", book.available_copies == 2)
    expect_error("лишний возврат невозможен",
                 DomainInvariantViolation, book.return_copy)


# ---------- FullName, TicketNumber, BookCopy, Fine ----------
def test_library_values() -> None:
    print("\n--- VO библиотеки ---")

    full_name = FullName("Иван", "Иванов", "Иванович")
    check("FullName строкой: 'Иванов Иван Иванович'",
          str(full_name) == "Иванов Иван Иванович")
    expect_error("FullName: пустое имя",
                 InvalidValueObject, lambda: FullName("", "Иванов"))
    expect_error("FullName: пустая фамилия",
                 InvalidValueObject, lambda: FullName("Иван", ""))

    expect_error("TicketNumber: пустой",
                 InvalidValueObject, lambda: TicketNumber(""))
    expect_error("TicketNumber: слишком короткий",
                 InvalidValueObject, lambda: TicketNumber("X"))
    no_error("TicketNumber: корректный",
             lambda: TicketNumber("ЧБ-0001"))

    book_id = Book.create("X", "Y", 3).book_id
    copy = BookCopy(book_id, 3)
    check("BookCopy.take_one уменьшает количество",
          copy.take_one().quantity == 2)
    check("BookCopy.add_one увеличивает количество",
          copy.add_one().quantity == 4)
    expect_error("BookCopy: quantity < 1",
                 InvalidValueObject, lambda: BookCopy(book_id, 0))

    fine = Fine.for_overdue(5, Money(Decimal("100")))
    check("Fine.for_overdue: 5 × 100 = 500",
          fine.amount == Money(Decimal("500")))
    check("Fine: days_overdue = 5", fine.days_overdue == 5)
    expect_error("Fine: отрицательная сумма",
                 InvalidValueObject,
                 lambda: Fine(Money(Decimal("10")), days_overdue=-1))


# ---------- Reader ----------
def test_reader() -> None:
    print("\n--- Reader (инвариант: заблокированному не выдаём) ---")
    reader = Reader.create(
        FullName("Иван", "Иванов", "Иванович"),
        TicketNumber("ЧБ-0001"),
    )
    check("активен при создании", reader.is_active())

    reader.block()
    check("после блокировки не активен", not reader.is_active())
    expect_error("повторная блокировка запрещена",
                 DomainInvariantViolation, reader.block)

    reader.unblock()
    check("после разблокировки активен", reader.is_active())
    expect_error("повторная разблокировка запрещена",
                 DomainInvariantViolation, reader.unblock)


# ---------- Loan ----------
def test_loan() -> None:
    print("\n--- Loan (инварианты 3, 4, 5, 6) ---")
    book_id = Book.create("X", "Y", 1).book_id
    loan = Loan.create(book_id, ReaderId(uuid4()),
                       date(2026, 1, 1), loan_days=14)
    check("создан активный Loan", loan.is_active())
    check("статус ISSUED", loan.status is LoanStatus.ISSUED)

    fine_per_day = Money(Decimal("100"))
    fine = loan.close(date(2026, 1, 15), fine_per_day)
    check("штраф за 1 день = 100",
          fine.amount == Money(Decimal("100")))
    check("дней просрочки = 1", fine.days_overdue == 1)
    check("статус CLOSED", loan.status is LoanStatus.CLOSED)
    expect_error("повторное закрытие запрещено",
                 DomainInvariantViolation,
                 lambda: loan.close(date(2026, 1, 15), fine_per_day))

    loan2 = Loan.create(book_id, ReaderId(uuid4()),
                        date(2026, 1, 1), loan_days=14)
    expect_error("возврат раньше выдачи",
                 DomainInvariantViolation,
                 lambda: loan2.close(date(2025, 12, 1), fine_per_day))

    loan3 = Loan.create(book_id, ReaderId(uuid4()),
                        date(2026, 1, 1), loan_days=14)
    fine0 = loan3.close(date(2026, 1, 10), fine_per_day)
    check("без просрочки штраф = 0",
          fine0.amount == Money(Decimal("0")))
    check("дней просрочки = 0", fine0.days_overdue == 0)


# ---------- LibraryService ----------
def test_library_service() -> None:
    print("\n--- LibraryService ---")
    service = LibraryService(fine_per_day=Money(Decimal("100")))
    book = Book.create("Тест", "Автор", 1)
    reader = Reader.create(
        FullName("Пётр", "Петров"),
        TicketNumber("ЧБ-0099"),
    )

    today = date.today()
    loan = service.issue_book(book, reader, today, loan_days=14)
    check("выдача уменьшила available", book.available_copies == 0)

    fine = service.return_book(book, loan, today + timedelta(days=15))
    check("штраф 1 день = 100",
          fine.amount == Money(Decimal("100")))
    check("возврат вернул экземпляр", book.available_copies == 1)

    expect_error("повторный возврат через сервис",
                 DomainInvariantViolation,
                 lambda: service.return_book(book, loan,
                                             today + timedelta(days=15)))

    expect_error("выдача в прошлом",
                 DomainInvariantViolation,
                 lambda: service.issue_book(
                     book, reader, today - timedelta(days=1)))

    # --- Заблокированный читатель ---
    reader.block()
    expect_error("заблокированному читателю книгу не выдаём",
                 DomainInvariantViolation,
                 lambda: service.issue_book(book, reader, today))


# ---------- ParkingSpot ----------
def test_parking_spot() -> None:
    print("\n--- ParkingSpot (инварианты 1, 2) ---")
    spot = ParkingSpot.create("A-01")
    check("новое место свободно", spot.is_free())
    check("статус FREE", spot.status is SpotStatus.FREE)

    session = ParkingSession.create(
        spot.spot_id, VehicleId(uuid4()), LicensePlate("А123ВС77"),
        datetime.now(),
    )
    spot.occupy(session.session_id)
    check("после occupy место занято", not spot.is_free())
    check("статус OCCUPIED", spot.status is SpotStatus.OCCUPIED)
    check("active_session_id сохранён",
          spot.active_session_id == session.session_id)

    expect_error("повторный occupy запрещён",
                 DomainInvariantViolation,
                 lambda: spot.occupy(session.session_id))

    spot.release()
    check("после release место свободно", spot.is_free())
    check("active_session_id = None", spot.active_session_id is None)
    expect_error("release свободного места запрещён",
                 DomainInvariantViolation, spot.release)


# ---------- ParkingSession ----------
def test_parking_session() -> None:
    print("\n--- ParkingSession (инварианты 2, 3, 4, 5) ---")
    spot = ParkingSpot.create("A-01")
    vehicle = VehicleId(uuid4())
    plate = LicensePlate("А123ВС77")
    entry = datetime(2026, 1, 1, 10, 0)
    session = ParkingSession.create(spot.spot_id, vehicle, plate, entry)

    check("создана активная сессия", session.is_active())
    check("статус ACTIVE", session.status is SessionStatus.ACTIVE)
    check("license_plate сохранён", session.license_plate == plate)

    tariff = Tariff(hourly_rate=Money(Decimal("100")))
    cost = session.close(datetime(2026, 1, 1, 12, 30), tariff)
    check("стоимость = 300 (2ч30 → 3ч)", cost == Money(Decimal("300")))
    check("статус CLOSED", session.status is SessionStatus.CLOSED)
    check("время закрытия сохранено", session.interval.is_closed)
    check("total_due = cost без штрафа", session.total_due == cost)

    expect_error("повторное закрытие запрещено",
                 DomainInvariantViolation,
                 lambda: session.close(datetime(2026, 1, 1, 13), tariff))

    session2 = ParkingSession.create(spot.spot_id, vehicle, plate, entry)
    expect_error("выезд раньше въезда",
                 DomainInvariantViolation,
                 lambda: session2.close(datetime(2026, 1, 1, 9), tariff))

    # --- Штраф за превышение лимита ---
    session3 = ParkingSession.create(spot.spot_id, vehicle, plate, entry)
    policy = ParkingPolicy(max_hours=2,
                           overstay_fine=Money(Decimal("500")))
    session3.close(datetime(2026, 1, 1, 15, 0), tariff, policy)
    check("стоимость без штрафа = 500",
          session3.cost == Money(Decimal("500")))
    check("штраф = 500", session3.overstay_fine == Money(Decimal("500")))
    check("total_due = 1000",
          session3.total_due == Money(Decimal("1000")))

    # --- Без превышения — штрафа нет ---
    session4 = ParkingSession.create(spot.spot_id, vehicle, plate, entry)
    session4.close(datetime(2026, 1, 1, 11, 0), tariff, policy)
    check("без превышения штраф = 0",
          session4.overstay_fine == Money(Decimal("0")))


# ---------- ParkingService ----------
def test_parking_service() -> None:
    print("\n--- ParkingService ---")
    spot = ParkingSpot.create("A-01")
    vehicle = VehicleId(uuid4())
    plate = LicensePlate("А123ВС77")
    service = ParkingService()
    tariff = Tariff(hourly_rate=Money(Decimal("100")), minimum_hours=1)
    sessions = InMemoryParkingSessionRepository()

    entry = datetime(2026, 1, 1, 10)
    session = service.start_session(
        spot, vehicle, plate, entry,
        active_session_lookup=sessions.find_active_by_vehicle,
    )
    sessions.save(session)

    check("после старта место занято", not spot.is_free())
    check("сессия привязана к месту", session.spot_id == spot.spot_id)

    expect_error("второй старт на том же месте",
                 DomainInvariantViolation,
                 lambda: service.start_session(
                     spot, vehicle, plate, entry,
                     active_session_lookup=sessions.find_active_by_vehicle,
                 ))

    # Попытка въехать той же машиной на другое место
    spot2 = ParkingSpot.create("A-02")
    expect_error("машина уже на парковке",
                 DomainInvariantViolation,
                 lambda: service.start_session(
                     spot2, vehicle, plate, entry,
                     active_session_lookup=sessions.find_active_by_vehicle,
                 ))

    cost = service.end_session(spot, session, datetime(2026, 1, 1, 11, 30),
                               tariff)
    sessions.save(session)
    check("стоимость 2 часа = 200 (1ч30 → 2ч)",
          cost == Money(Decimal("200")))
    check("после конца место свободно", spot.is_free())

    expect_error("повторный end_session",
                 DomainInvariantViolation,
                 lambda: service.end_session(
                     spot, session, datetime(2026, 1, 1, 12), tariff))


# ---------- main ----------
if __name__ == "__main__":
    print("=" * 60)
    print("ПРОВЕРКА ИНВАРИАНТОВ ЛАБОРАТОРНОЙ РАБОТЫ №2")
    print("=" * 60)

    test_value_objects()
    test_book()
    test_library_values()
    test_reader()
    test_loan()
    test_library_service()
    test_parking_spot()
    test_parking_session()
    test_parking_service()

    print()
    print("=" * 60)
    print(f"ИТОГО: пройдено {PASSED}, провалено {FAILED}")
    print("=" * 60)