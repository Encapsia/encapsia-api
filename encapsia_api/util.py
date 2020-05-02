import uuid

from .credentials import discover_credentials
from .rest import EncapsiaApi

__all__ = ["get_api_from_api_or_host", "make_uuid"]


def get_api_from_api_or_host(api_or_host):
    """Convenience to support functions taking either host name or pre-existing api."""
    if isinstance(api_or_host, EncapsiaApi):
        return api_or_host
    else:
        url, token = discover_credentials(api_or_host)
        return EncapsiaApi(url, token)


def make_uuid():
    """Generate and return new uuid typically used in encapsia."""
    return uuid.uuid4().hex
