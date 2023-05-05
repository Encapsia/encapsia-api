import io
from contextlib import suppress
from unittest import mock

import pytest
import requests

from encapsia_api import resilient_request


# commonly used URL and response for mocker and request
URL = "https://localhost/dev/null"
RESPONSE = "ok"


_HTTP_VERBS_IDEMPOTENT = ["get", "head", "options", "delete"]
# we'll not consider put and delete as idempotent because of the ICE audit trail
_HTTP_VERBS_NON_IDEMPOTENT = ["put", "post", "patch"]


@pytest.fixture(
    scope="module",
    params=_HTTP_VERBS_IDEMPOTENT + _HTTP_VERBS_NON_IDEMPOTENT,
)
def http_verb(request):
    return request.param


@pytest.fixture(
    scope="module",
    params=_HTTP_VERBS_IDEMPOTENT,
)
def idempotent_http_verb(request):
    return request.param


@pytest.fixture(
    scope="module",
    params=_HTTP_VERBS_NON_IDEMPOTENT,
)
def non_idempotent_http_verb(request):
    return request.param


_ALWAYS_RETRIABLE_ERROR_RESPONSES = [
    {"exc": requests.exceptions.ConnectionError},
    {"exc": requests.exceptions.ConnectTimeout},
    {"status_code": 503},
]
_TIMEOUT_ERROR_RESPONSES = [
    {"exc": requests.exceptions.Timeout},
    {"status_code": 504},
]
_NON_RETRIABLE_ERROR_RESPONSES = [
    {"exc": requests.exceptions.TooManyRedirects},
    {"status_code": 401},
    {"status_code": 403},
    {"status_code": 404},
    {"status_code": 500},
    {"status_code": 501},
    {"status_code": 502},
]


@pytest.fixture(
    scope="module",
    params=_ALWAYS_RETRIABLE_ERROR_RESPONSES,
)
def always_retriable_response(request):
    return request.param


@pytest.fixture(
    scope="module",
    params=_TIMEOUT_ERROR_RESPONSES,
)
def timeout_response(request):
    return request.param


@pytest.fixture(
    scope="module",
    params=_NON_RETRIABLE_ERROR_RESPONSES,
)
def non_retriable_error_response(request):
    return request.param


@pytest.fixture(
    scope="module", params=_ALWAYS_RETRIABLE_ERROR_RESPONSES + _TIMEOUT_ERROR_RESPONSES
)
def error_response(request):
    return request.param


def test_call_once_if_success(requests_mock):
    requests_mock.get(URL, text=RESPONSE)
    result = resilient_request.resilient_request("get", URL)
    assert requests_mock.call_count == 1
    assert result.text == RESPONSE


def test_default_timeout_is_set(requests_mock):
    requests_mock.get(URL, json=RESPONSE)
    resilient_request.resilient_request("get", URL)
    assert requests_mock.last_request.timeout == resilient_request.DEFAULT_TIMEOUT


def test_custom_timeout_is_set(requests_mock):
    requests_mock.get(URL, json=RESPONSE)
    resilient_request.resilient_request("get", URL, timeout=10)
    assert requests_mock.last_request.timeout == 10


def test_retry_on_continuing_error_than_raise(requests_mock):
    requests_mock.get(URL, exc=requests.exceptions.ConnectionError)
    with pytest.raises(requests.exceptions.ConnectionError):
        resilient_request.resilient_request("get", URL, retry_delay=(0, 0))
    assert requests_mock.call_count == resilient_request.DEFAULT_RETRIES


def test_retry_a_on_error_than_return_response_on_success(requests_mock):
    requests_mock.get(
        URL,
        [
            {"exc": requests.exceptions.ConnectionError},
            {"text": RESPONSE},
        ],
    )
    result = resilient_request.resilient_request("get", URL, retry_delay=(0, 0))
    assert requests_mock.call_count == 2
    assert result.text == RESPONSE


def test_callback_not_called_if_success(requests_mock):
    callback_called = False

    def set_called(*_):
        nonlocal callback_called
        callback_called = True

    requests_mock.get(URL, text=RESPONSE)
    resilient_request.resilient_request(
        "get", URL, retry_delay=(0, 0), on_retry=set_called
    )
    assert callback_called is False


def test_callback_called_on_each_retry(requests_mock):
    callback_count = 0

    def set_called(count, response_or_error, _):
        nonlocal callback_count
        callback_count += 1
        assert count == callback_count
        assert isinstance(response_or_error, requests.exceptions.ConnectionError)

    requests_mock.get(URL, exc=requests.exceptions.ConnectionError)
    with suppress(requests.exceptions.ConnectionError):
        resilient_request.resilient_request(
            "get", URL, retry_delay=(0, 0), on_retry=set_called
        )
    assert requests_mock.call_count == callback_count


def test_data_uploaded_again_on_retry(requests_mock):
    test_data = "some data"
    requests_mock.get(
        URL,
        [
            {"exc": requests.exceptions.ConnectionError},
            {"text": RESPONSE},
        ],
    )
    result = resilient_request.resilient_request(
        "get",
        URL,
        retry_delay=(0, 0),
        data=test_data,
    )
    assert requests_mock.call_count == 2
    assert result.text == RESPONSE
    for request in requests_mock.request_history:
        assert request.text == test_data


def test_callback_can_rewind_data(requests_mock, tmp_path):
    test_data = "some data\nsome more data\n"

    def mock_err_callback(request, context):
        data = request.text.read()
        assert data == test_data.encode()
        context.status_code = 503
        return RESPONSE

    def mock_text_callback(request, context):
        data = request.text.read()
        assert data == test_data.encode()
        context.status_code = 200
        return RESPONSE

    def on_retry(count, response_or_error, data):
        data.seek(0, io.SEEK_SET)

    requests_mock.get(
        URL,
        [
            {"text": mock_err_callback},
            {"text": mock_text_callback},
        ],
    )
    data_file = tmp_path / "data.txt"
    data_file.write_text(test_data)

    with open(data_file, "rb") as f:
        result = resilient_request.resilient_request(
            "get", URL, retry_delay=(0, 0), on_retry=on_retry, data=f
        )
    assert requests_mock.call_count > 1  # ensure retry occured
    assert result.text == RESPONSE


def test_callback_can_prevent_retry(requests_mock):
    def on_retry(*a):
        return False

    requests_mock.get(
        URL,
        [
            {"exc": requests.exceptions.ConnectionError},
            {"text": RESPONSE},
        ],
    )
    with pytest.raises(requests.exceptions.ConnectionError):
        resilient_request.resilient_request(
            "get",
            URL,
            retry_delay=(0, 0),
            on_retry=on_retry,
        )
    assert requests_mock.call_count == 1


def test_always_retriable_errors(requests_mock, http_verb, always_retriable_response):
    requests_mock.request(http_verb, URL, **always_retriable_response)
    with suppress(requests.exceptions.RequestException):
        resilient_request.resilient_request(
            http_verb, URL, retries=2, retry_delay=(0, 0)
        )
    assert requests_mock.call_count == 2


def test_retry_on_timeout_if_implicitly_idempotent(
    requests_mock, idempotent_http_verb, timeout_response
):
    requests_mock.request(idempotent_http_verb, URL, **timeout_response)
    with suppress(requests.exceptions.RequestException):
        resilient_request.resilient_request(
            idempotent_http_verb, URL, retries=2, retry_delay=(0, 0)
        )
    assert requests_mock.call_count == 2


def test_retry_on_timeout_if_explicitly_idempotent(
    requests_mock, http_verb, timeout_response
):
    requests_mock.request(http_verb, URL, **timeout_response)
    with suppress(requests.exceptions.RequestException):
        resilient_request.resilient_request(
            http_verb, URL, is_idempotent=True, retries=2, retry_delay=(0, 0)
        )
    assert requests_mock.call_count == 2


def test_no_retry_on_timeout_if_not_idempotent(
    requests_mock, non_idempotent_http_verb, timeout_response
):
    requests_mock.request(non_idempotent_http_verb, URL, **timeout_response)
    with suppress(requests.exceptions.RequestException):
        resilient_request.resilient_request(
            non_idempotent_http_verb, URL, retries=2, retry_delay=(0, 0)
        )
    assert requests_mock.call_count == 1


def test_no_retry_on_non_retriable_erros(
    requests_mock, http_verb, non_retriable_error_response
):
    requests_mock.request(http_verb, URL, **non_retriable_error_response)
    with suppress(requests.exceptions.RequestException):
        resilient_request.resilient_request(
            http_verb, URL, retries=2, retry_delay=(0, 0)
        )
    assert requests_mock.call_count == 1


@mock.patch.object(resilient_request, "_backoff_delay", return_value=0)
def test_backoff_delay_called_on_retry(mock_backoff_delay, requests_mock):
    requests_mock.get(URL, exc=requests.exceptions.ConnectionError)
    with suppress(requests.exceptions.ConnectionError):
        resilient_request.resilient_request("get", URL, retries=5, retry_delay=(1, 2))
    print(mock_backoff_delay.call_args_list)
    assert mock_backoff_delay.call_args_list == [
        mock.call(i, (1, 2)) for i in range(1, 6)
    ]


def test_retry_delay_between_min_and_max():
    for i in range(10):
        assert resilient_request._backoff_delay(i, 60) <= 60
        assert 40 <= resilient_request._backoff_delay(i, (40, 200)) <= 200
