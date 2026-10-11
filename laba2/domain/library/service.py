from datetime import date

from domain.common.exceptions import DomainInvariantViolation
from domain.common.values import Money
from domain.library.aggregates import Book, Loan, Reader
from domain.library.values import Fine


class LibraryService:
    """
    Доменный сервис библиотеки.
    Координирует операции, затрагивающие Book, Reader и Loan.
    """

    def __init__(self, fine_per_day: Money) -> None:
        self._fine_per_day = fine_per_day

    def issue_book(self, book: Book, reader: Reader,
                   issue_date: date, loan_days: int = 14) -> Loan:
        if issue_date < date.today():
            raise DomainInvariantViolation(
                "Дата выдачи не может быть в прошлом"
            )
        if not reader.is_active():
            raise DomainInvariantViolation(
                f"Читатель {reader.full_name} заблокирован"
            )
        book.issue_copy()
        return Loan.create(book.book_id, reader.reader_id,
                           issue_date, loan_days)

    def return_book(self, book: Book, loan: Loan,
                    return_date: date) -> Fine:
        if not loan.is_active():
            raise DomainInvariantViolation("Выдача уже закрыта")
        if loan.book_id != book.book_id:
            raise DomainInvariantViolation("Выдача не соответствует книге")

        fine = loan.close(return_date, self._fine_per_day)
        book.return_copy()
        return fine