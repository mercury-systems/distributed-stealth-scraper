"""Custom exceptions."""


class InvalidURLError(ValueError):
    pass


class ProxyError(Exception):
    pass


class ProxyExhaustedError(Exception):
    pass


class TimeoutError(Exception):
    pass


class UnknownFetchError(Exception):
    pass


class ChallengeNotSolvedError(Exception):
    pass
