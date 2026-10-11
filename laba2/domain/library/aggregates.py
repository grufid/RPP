from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from uuid import uuid4

from domain.common.exceptions import DomainInvariantViolation, EntityNotFound
from domain.common.values import Money
from domain.library.values import (
    BookId, CopyId, Fine, FullName, ISBN, LoanId, LoanPeriod,
    ReaderId, TicketNumber,
)


class LoanStatus(Enum):
    ISSUED = "выдана"
    CLOSED = "закрыта"


@dataclass(frozen=True)
class Copy:
    id: CopyId
    on_loan: bool = False


class Book:

    def __init__(self, book_id: BookId, title: str, author: str,
                 isbn: ISBN, copies: list[Copy] | None = None) -> None:
        if not title.strip():
            raise DomainInvariantViolation("Название книги не может быть пустым")
        if not author.strip():
            raise DomainInvariantViolation("Автор не может быть пустым")

        self._book_id = book_id
        self._title = title
        self._author = author
        self._isbn = isbn
        self._copies: list[Copy] = list(copies) if copies else []

    @property
    def book_id(self) -> BookId: return self._book_id
    @property
    def title(self) -> str: return self._title
    @property
    def author(self) -> str: return self._author
    @property
    def isbn(self) -> ISBN: return self._isbn

    def copies(self) -> tuple[Copy, ...]:
        return tuple(self._copies)

    def total_count(self) -> int:
        return len(self._copies)

    def available_count(self) -> int:
        return sum(1 for c in self._copies if not c.on_loan)

    @classmethod
    def create(cls, title: str, author: str, isbn: ISBN) -> "Book":
        return cls(BookId(uuid4()), title, author, isbn)

    @classmethod
    def restore(cls, book_id: BookId, title: str, author: str,
                isbn: ISBN, copies: list[Copy]) -> "Book":
        return cls(book_id, title, author, isbn, copies)

    def add_copy(self) -> CopyId:
        copy = Copy(id=CopyId(uuid4()))
        self._copies.append(copy)
        return copy.id

    def _find_copy_index(self, copy_id: CopyId) -> int:
        for i, c in enumerate(self._copies):
            if c.id == copy_id:
                return i
        raise EntityNotFound(
            f"Экземпляр {copy_id.value} не найден в книге «{self._title}»"
        )

    def checkout(self, copy_id: CopyId) -> None:
        """Инварианты: нет свободных; экземпляр уже выдан."""
        if self.available_count() <= 0:
            raise DomainInvariantViolation(
                f"Нет свободных экземпляров книги «{self._title}»"
            )
        i = self._find_copy_index(copy_id)
        if self._copies[i].on_loan:
            raise DomainInvariantViolation(
                "Этот экземпляр уже выдан другому читателю"
            )
        self._copies[i] = Copy(id=copy_id, on_loan=True)

    def return_copy(self, copy_id: CopyId) -> None:
        """Инвариант: нельзя вернуть невыданный экземпляр."""
        i = self._find_copy_index(copy_id)
        if not self._copies[i].on_loan:
            raise DomainInvariantViolation(
                "Нельзя вернуть экземпляр, который не выдан"
            )
        self._copies[i] = Copy(id=copy_id, on_loan=False)


class Reader:
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

    def is_active(self) -> bool:
        return self._is_active

    @classmethod
    def create(cls, full_name: FullName,
               ticket_number: TicketNumber) -> "Reader":
        return cls(ReaderId(uuid4()), full_name, ticket_number)

    @classmethod
    def restore(cls, reader_id: ReaderId, full_name: FullName,
                ticket_number: TicketNumber,
                is_active: bool = True) -> "Reader":
        return cls(reader_id, full_name, ticket_number, is_active)

    def block(self) -> None:
        if not self._is_active:
            raise DomainInvariantViolation("Читатель уже заблокирован")
        self._is_active = False

    def unblock(self) -> None:
        if self._is_active:
            raise DomainInvariantViolation("Читатель уже активен")
        self._is_active = True


class Loan:
    def __init__(self, loan_id: LoanId, book_id: BookId, copy_id: CopyId,
                 reader_id: ReaderId, period: LoanPeriod,
                 status: LoanStatus = LoanStatus.ISSUED,
                 fine: Fine | None = None) -> None:
        self._loan_id = loan_id
        self._book_id = book_id
        self._copy_id = copy_id
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
    def copy_id(self) -> CopyId: return self._copy_id
    @property
    def reader_id(self) -> ReaderId: return self._reader_id
    @property
    def period(self) -> LoanPeriod: return self._period
    @property
    def status(self) -> LoanStatus: return self._status
    @property
    def fine(self) -> Fine | None: return self._fine

    @classmethod
    def create(cls, book_id: BookId, copy_id: CopyId, reader_id: ReaderId,
               issue_date: date, loan_days: int) -> "Loan":
        period = LoanPeriod(
            issue_date=issue_date,
            due_date=issue_date + timedelta(days=loan_days),
        )
        return cls(LoanId(uuid4()), book_id, copy_id, reader_id, period)

    @classmethod
    def restore(cls, loan_id: LoanId, book_id: BookId, copy_id: CopyId,
                reader_id: ReaderId, period: LoanPeriod,
                status: LoanStatus, fine: Fine | None = None) -> "Loan":
        return cls(loan_id, book_id, copy_id, reader_id, period, status, fine)

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
        self._fine = Fine.for_overdue(self._period.overdue_days(), fine_per_day)
        self._status = LoanStatus.CLOSED
        return self._fine