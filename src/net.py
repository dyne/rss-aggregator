"""Small network safety helpers used by feed and metadata fetchers."""


class ResponseTooLarge(ValueError):
    """Raised when a remote response body exceeds the configured byte limit."""


def read_limited_bytes(response, limit, close=False):
    """Read response bytes up to *limit* and fail when limit is exceeded."""
    try:
        body = response.read(limit + 1)
    finally:
        if close:
            response.close()
    if len(body) > limit:
        raise ResponseTooLarge("response exceeds byte limit")
    return body
