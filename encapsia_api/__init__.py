#: Keep in sync with git tag and package version in pyproject.toml.
__version__ = "0.1.25"


class EncapsiaApiError(RuntimeError):  # NOQA
    def __init__(self, message, payload=None):
        super().__init__(message)
        self.message = message
        self.payload = payload


class EncapsiaApiFailedTaskError(EncapsiaApiError):  # NOQA
    pass


from encapsia_api.analytics import *  # NOQA
from encapsia_api.credentials import *  # NOQA
from encapsia_api.package import *  # NOQA
from encapsia_api.plugin import *  # NOQA
from encapsia_api.rest import *  # NOQA
from encapsia_api.util import *  # NOQA
