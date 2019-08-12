#: Keep in sync with git tag and package version in pyproject.toml.
__version__ = "0.1.21"


class EncapsiaApiError(RuntimeError):  # NOQA
    def __init__(self, message, payload=None):
        super().__init__(message)
        self.message = message
        self.payload = payload


class EncapsiaApiFailedTaskError(EncapsiaApiError):  # NOQA
    pass


from encapsia_api.credentials import CredentialsStore  # NOQA
from encapsia_api.credentials import discover_credentials  # NOQA
from encapsia_api.package import PackageMaker  # NOQA
from encapsia_api.rest import EncapsiaApi  # NOQA
from encapsia_api.rest import FileDownloadResponse  # NOQA
