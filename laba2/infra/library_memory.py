from typing import Optional, Protocol
from uuid import UUID

from domain.library.aggregates import Book, Loan, Reader
from domain.library.values import BookId, LoanId, ReaderId


class BookRepository(Protocol):
    def save(self, book: Book) -> None: ...
    def get(self, book_id: BookId) -> Optional[Book]: ...


class ReaderRepository(Protocol):
    def save(self, reader: Reader) -> None: ...
    def get(self, reader_id: ReaderId) -> Optional[Reader]: ...


class LoanRepository(Protocol):
    def save(self, loan: Loan) -> None: ...
    def get(self, loan_id: LoanId) -> Optional[Loan]: ...


class InMemoryBookRepository:
    def __init__(self) -> None:
        self._storage: dict[UUID, Book] = {}

    def save(self, book: Book) -> None:
        self._storage[book.book_id.value] = book

    def get(self, book_id: BookId) -> Optional[Book]:
        return self._storage.get(book_id.value)


class InMemoryReaderRepository:
    def __init__(self) -> None:
        self._storage: dict[UUID, Reader] = {}

    def save(self, reader: Reader) -> None:
        self._storage[reader.reader_id.value] = reader

    def get(self, reader_id: ReaderId) -> Optional[Reader]:
        return self._storage.get(reader_id.value)


class InMemoryLoanRepository:
    def __init__(self) -> None:
        self._storage: dict[UUID, Loan] = {}

    def save(self, loan: Loan) -> None:
        self._storage[loan.loan_id.value] = loan

    def get(self, loan_id: LoanId) -> Optional[Loan]:
        return self._storage.get(loan_id.value)