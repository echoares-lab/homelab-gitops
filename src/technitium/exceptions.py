"""Technitium DNS Server API client exceptions"""


class TechnitiumError(Exception):
    pass


class TechnitiumAPIError(TechnitiumError):
    pass


class TechnitiumBadRequest(TechnitiumAPIError):
    pass


class TechnitiumUnauthorized(TechnitiumAPIError):
    pass


class TechnitiumServerError(TechnitiumAPIError):
    pass


class TechnitiumTimeoutError(TechnitiumError):
    pass


class TechnitiumValidationError(TechnitiumError):
    pass
