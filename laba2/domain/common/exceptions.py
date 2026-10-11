class DomainError(Exception):
    """Базовое доменное исключение."""


class DomainInvariantViolation(DomainError):
    """Нарушение инварианта агрегата."""


class InvalidValueObject(DomainError):
    """Некорректное значение объекта-значения."""


class EntityNotFound(DomainError):
    """Сущность не найдена в репозитории."""