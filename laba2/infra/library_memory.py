from uuid import UUID

from domain.common.exceptions import EntityNotFound
from domain.library.aggregates import Book, Loan, Reader
from domain.library.values import BookId, LoanId, ReaderId


class InMemoryBookRepository:
    def __init__(self) -> None:
        self._storage: dict[UUID, Book] = {}

    def get(self, book_id: BookId) -> Book:
        try:
            return self._storage[book_id.value]
        except KeyError:
            raise EntityNotFound(f"Book {book_id.value} не найден")

    def save(self, book: Book) -> None:
        self._storage[book.book_id.value] = book


class InMemoryReaderRepository:
    def __init__(self) -> None:
        self._storage: dict[UUID, Reader] = {}

    def get(self, reader_id: ReaderId) -> Reader:
        try:
            return self._storage[reader_id.value]
        except KeyError:
            raise EntityNotFound(f"Reader {reader_id.value} не найден")

    def save(self, reader: Reader) -> None:
        self._storage[reader.reader_id.value] = reader


class InMemoryLoanRepository:
    def __init__(self) -> None:
        self._storage: dict[UUID, Loan] = {}

    def get(self, loan_id: LoanId) -> Loan:
        try:
            return self._storage[loan_id.value]
        except KeyError:
            raise EntityNotFound(f"Loan {loan_id.value} не найден")

    def save(self, loan: Loan) -> None:
        self._storage[loan.loan_id.value] = loan