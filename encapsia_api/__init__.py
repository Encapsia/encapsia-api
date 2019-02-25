#: Keep in sync with git tag and package version in pyproject.toml.
__version__ = "0.1.14"


class EncapsiaApiError(RuntimeError):  # NOQA
    pass


from encapsia_api.credentials import CredentialsStore, discover_credentials  # NOQA
from encapsia_api.rest import EncapsiaApi  # NOQA
