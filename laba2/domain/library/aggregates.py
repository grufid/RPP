from datetime import date, timedelta
from enum import Enum
from uuid import uuid4

from domain.common.exceptions import DomainInvariantViolation
from domain.library.values import (
    BookCopy, BookId, Fine, FullName, LoanId, LoanPeriod,
    ReaderId, TicketNumber,
)
from domain.common.values import Money

class LoanStatus(Enum):
    ISSUED = "выдана"
    CLOSED = "закрыта"


class Book:
    """
    Агрегат-корень «Книга».
    Хранит метаданные и количество доступных экземпляров.
    Инвариант: 0 <= available_copies <= total_copies.
    """

    def __init__(self, book_id: BookId, title: str, author: str,
                 total_copies: int, available_copies: int) -> None:
        self._book_id = book_id
        self._title = title
        self._author = author
        self._total_copies = total_copies
        self._available_copies = available_copies
        self._check_invariants()

    def _check_invariants(self) -> None:
        if self._total_copies <= 0:
            raise DomainInvariantViolation("Всего экземпляров должно быть > 0")
        if not (0 <= self._available_copies <= self._total_copies):
            raise DomainInvariantViolation(
                "Доступных экземпляров должно быть от 0 до total"
            )

    @property
    def book_id(self) -> BookId: return self._book_id
    @property
    def title(self) -> str: return self._title
    @property
    def author(self) -> str: return self._author
    @property
    def total_copies(self) -> int: return self._total_copies
    @property
    def available_copies(self) -> int: return self._available_copies

    @property
    def copy(self) -> BookCopy:
        """VO-представление доступных экземпляров."""
        return BookCopy(self._book_id, self._available_copies)

    @classmethod
    def create(cls, title: str, author: str, total: int) -> "Book":
        return cls(BookId(uuid4()), title, author, total, total)

    @classmethod
    def restore(cls, book_id: BookId, title: str, author: str,
                total: int, available: int) -> "Book":
        return cls(book_id, title, author, total, available)

    def issue_copy(self) -> None:
        if self._available_copies <= 0:
            raise DomainInvariantViolation(
                f"Нет свободных экземпляров книги «{self._title}»"
            )
        self._available_copies -= 1

    def return_copy(self) -> None:
        if self._available_copies >= self._total_copies:
            raise DomainInvariantViolation(
                "Нельзя вернуть больше экземпляров, чем выдано"
            )
        self._available_copies += 1


class Reader:
    """
    Агрегат-корень «Читатель».
    Инвариант: заблокированному читателю книгу не выдаём.
    """

    def __init__(self, reader_id: ReaderId, full_name: FullName,
                 ticket_number: TicketNumber,
                 is_active: bool = True) -> None:
        self._reader_id = reader_id
        self._full_name = full_name
        self._ticket_number = ticket_number
        self._is_active = is_active

    @property
    def reader_id(self) -> ReaderId: return self._reader_id
    @property
    def full_name(self) -> FullName: return self._full_name
    @property
    def ticket_number(self) -> TicketNumber: return self._ticket_number
    @property
    def is_active_flag(self) -> bool: return self._is_active

    @classmethod
    def create(cls, full_name: FullName,
               ticket_number: TicketNumber) -> "Reader":
        return cls(ReaderId(uuid4()), full_name, ticket_number)

    @classmethod
    def restore(cls, reader_id: ReaderId, full_name: FullName,
                ticket_number: TicketNumber,
                is_active: bool = True) -> "Reader":
        return cls(reader_id, full_name, ticket_number, is_active)

    def is_active(self) -> bool:
        return self._is_active

    def block(self) -> None:
        if not self._is_active:
            raise DomainInvariantViolation("Читатель уже заблокирован")
        self._is_active = False

    def unblock(self) -> None:
        if self._is_active:
            raise DomainInvariantViolation("Читатель уже активен")
        self._is_active = True


class Loan:
    """
    Агрегат-корень «Выдача».
    Связи с Book и Reader — по идентификаторам.
    Хранит экземпляр (book_id + количество) и штраф как VO Fine.
    """

    def __init__(self, loan_id: LoanId, book_id: BookId,
                 reader_id: ReaderId, period: LoanPeriod,
                 status: LoanStatus,
                 fine: Fine | None = None) -> None:
        self._loan_id = loan_id
        self._book_id = book_id
        self._reader_id = reader_id
        self._period = period
        self._status = status
        self._fine = fine
        self._check_invariants()

    def _check_invariants(self) -> None:
        if self._status is LoanStatus.CLOSED and self._period.return_date is None:
            raise DomainInvariantViolation("Закрытая выдача без даты возврата")
        if self._status is LoanStatus.ISSUED and self._period.return_date is not None:
            raise DomainInvariantViolation("Активная выдача с датой возврата")

    @property
    def loan_id(self) -> LoanId: return self._loan_id
    @property
    def book_id(self) -> BookId: return self._book_id
    @property
    def reader_id(self) -> ReaderId: return self._reader_id
    @property
    def period(self) -> LoanPeriod: return self._period
    @property
    def status(self) -> LoanStatus: return self._status
    @property
    def fine(self) -> Fine | None: return self._fine

    @property
    def copy(self) -> BookCopy:
        """VO-представление выданного экземпляра (1 шт.)."""
        return BookCopy(self._book_id, 1)

    @classmethod
    def create(cls, book_id: BookId, reader_id: ReaderId,
               issue_date: date, loan_days: int) -> "Loan":
        period = LoanPeriod(
            issue_date=issue_date,
            due_date=issue_date + timedelta(days=loan_days),
        )
        return cls(LoanId(uuid4()), book_id, reader_id, period, LoanStatus.ISSUED)

    @classmethod
    def restore(cls, loan_id: LoanId, book_id: BookId, reader_id: ReaderId,
                period: LoanPeriod, status: LoanStatus,
                fine: Fine | None = None) -> "Loan":
        return cls(loan_id, book_id, reader_id, period, status, fine)

    def is_active(self) -> bool:
        return self._status is LoanStatus.ISSUED

    def close(self, return_date: date, fine_per_day: Money) -> Fine:
        if self._status is LoanStatus.CLOSED:
            raise DomainInvariantViolation("Выдача уже закрыта")
        if return_date < self._period.issue_date:
            raise DomainInvariantViolation("Дата возврата раньше даты выдачи")

        self._period = LoanPeriod(
            issue_date=self._period.issue_date,
            due_date=self._period.due_date,
            return_date=return_date,
        )
        days = self._period.overdue_days()
        self._fine = Fine.for_overdue(days, fine_per_day)
        self._status = LoanStatus.CLOSED
        return self._fine