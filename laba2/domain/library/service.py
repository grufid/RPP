from datetime import date

from domain.common.exceptions import DomainInvariantViolation
from domain.common.values import Money
from domain.library.aggregates import Loan
from domain.library.repositories import (
    BookRepository, LoanRepository, ReaderRepository,
)
from domain.library.values import BookId, CopyId, Fine, LoanId, ReaderId


class LibraryService:
    """
    Доменный сервис библиотеки.
    Координирует операции, затрагивающие Book, Reader и Loan.
    Сам держит репозитории и сохраняет изменённые агрегаты.
    """

    def __init__(self, books: BookRepository, readers: ReaderRepository,
                 loans: LoanRepository, fine_per_day: Money) -> None:
        self._books = books
        self._readers = readers
        self._loans = loans
        self._fine_per_day = fine_per_day

    def issue_book(self, book_id: BookId, copy_id: CopyId,
                   reader_id: ReaderId, issue_date: date,
                   loan_days: int = 14) -> Loan:
        if issue_date < date.today():
            raise DomainInvariantViolation(
                "Дата выдачи не может быть в прошлом"
            )

        book = self._books.get(book_id)
        reader = self._readers.get(reader_id)

        if not reader.is_active():
            raise DomainInvariantViolation(
                f"Читатель {reader.full_name} заблокирован"
            )

        book.checkout(copy_id)
        loan = Loan.create(book.book_id, copy_id, reader.reader_id,
                           issue_date, loan_days)

        self._books.save(book)
        self._loans.save(loan)
        return loan

    def return_book(self, loan_id: LoanId, return_date: date) -> Fine:
        loan = self._loans.get(loan_id)
        if not loan.is_active():
            raise DomainInvariantViolation("Выдача уже закрыта")

        book = self._books.get(loan.book_id)
        fine = loan.close(return_date, self._fine_per_day)
        book.return_copy(loan.copy_id)

        self._books.save(book)
        self._loans.save(loan)
        return fine