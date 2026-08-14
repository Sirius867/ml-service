class ServiceError(ValueError):
    pass


class InvalidDataError(ServiceError):
    pass


class AuthenticationError(ServiceError):
    pass


class NotFoundError(ServiceError):
    pass


class ConflictError(ServiceError):
    pass


class InsufficientBalanceError(ServiceError):
    pass


class BrokerError(ServiceError):
    pass
