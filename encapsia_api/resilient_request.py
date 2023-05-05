import random
import time
import typing as T

import requests
from requests.exceptions import ConnectionError, ConnectTimeout, Timeout


# recommended: slightly above (multiple of) initial TCP retransmit value of 3 seconds
CONNECT_TIMEOUT = 3 * 2 + 0.05

# timeout between receiving any two chunks of data, not the entire transfer
READ_TIMEOUT = 300

DEFAULT_TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)

# how many times to retry recoverable errors
DEFAULT_RETRIES = 3

# retry delay parametrization
MIN_MAX_DELAY_DISTANCE = 5
MAX_RETRY_DELAY = 60.0
MIN_RETRY_DELAY = 0.5
DEFAULT_RETRY_DELAY = (MIN_RETRY_DELAY, MAX_RETRY_DELAY)


RECOVERABLE_ERROR_CODES = frozenset({503, 504})
TIMEOUT_ERROR_CODES = frozenset({504})
ENCAPSIA_IDEMPOTENT_VERBS = frozenset({"get", "head", "options", "delete"})


def _should_retry(result, is_idempotent: bool) -> bool:
    if isinstance(result, requests.Response):
        if result.status_code in TIMEOUT_ERROR_CODES:
            return is_idempotent
        if result.status_code in RECOVERABLE_ERROR_CODES:
            return True
        return False
    if isinstance(result, (ConnectTimeout, ConnectionError)):
        return True
    if isinstance(result, Timeout):
        return is_idempotent
    return False


def _backoff_delay(count: int, delay: T.Union[float, T.Tuple[float, float]]) -> float:
    # Exponentially capped backoff with random jitter. With the default parameters,
    # delay will be between 0.5 and [10, 20, 40, 60, 60, ...] seconds.
    if isinstance(delay, tuple):
        min_delay, max_delay = delay
    else:
        min_delay, max_delay = MIN_RETRY_DELAY, delay
    d: float = max(
        min_delay,
        min(MIN_MAX_DELAY_DISTANCE * 2**count, max_delay)
        * random.random(),  # noqa: S311
    )
    return d


def resilient_request(
    method,
    url,
    timeout=DEFAULT_TIMEOUT,
    retries=DEFAULT_RETRIES,
    retry_delay=DEFAULT_RETRY_DELAY,
    on_retry=None,
    is_idempotent=None,
    **kwargs,
):
    """Call `requests.request()` and retry on errors when possible.

    :param method: HTTP verb to use.
    :param url: URL for the request.
    :param timeout: Timeout value (a float or a tuple) to pass to `requests`.
    :param retries: How many times to retry when errors are encountered.
    :param retry_delay: How long to wait between two retries.
    :param is_idempotent: Force a request to be considered idempotent.
    :returns: The response as returned by `requests`.

    Connection errors are always retried.

    Other errors are not automatically retried, except for some of the implicitly
    idempotent HTTP methods (get, head, options) or where the caller sets
    `is_idempotent` to `True`. Other HTTP methods that should be idempontent (put and
    delete) are not automatically retried, because due to the unavoidable audit trail
    they are not truly idempotent.

    """

    if is_idempotent is None:
        is_idempotent = method.lower() in ENCAPSIA_IDEMPOTENT_VERBS
    attempts = 0
    for attempts in range(1, retries + 1):
        got_exception = None
        got_response = None
        try:
            got_response = requests.request(
                method,
                url,
                timeout=timeout,
                **kwargs,
            )
            if got_response.status_code not in RECOVERABLE_ERROR_CODES:
                break
        except (ConnectTimeout, ConnectionError, Timeout) as e:
            got_exception = e
        response_or_error = got_exception if got_response is None else got_response
        if _should_retry(response_or_error, is_idempotent):
            if on_retry:
                data = kwargs.get("data")
                retry = on_retry(attempts, response_or_error, data)
                if retry is False:
                    break
            time.sleep(_backoff_delay(attempts, retry_delay))
            continue
        break

    if got_exception is not None:
        raise got_exception
    return got_response
