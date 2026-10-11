class DomainError(Exception):
    """Базовое доменное исключение."""
    pass


class DomainInvariantViolation(DomainError):
    """Нарушение инварианта предметной области."""
    pass


class InvalidValueObject(DomainError):
    """Некорректное значение объекта-значения."""
    pass