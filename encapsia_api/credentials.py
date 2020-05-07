import os
from pathlib import Path

import toml

import encapsia_api

__all__ = ["CredentialsStore", "discover_credentials"]


class CredentialsStore:
    CREDENTIALS_STORE = Path().home() / ".encapsia" / "credentials.toml"

    def __init__(self):
        # Create directory and file if they don't exist aleady
        self.CREDENTIALS_STORE.parent.mkdir(mode=0o700, exist_ok=True)
        self.CREDENTIALS_STORE.touch(mode=0o600, exist_ok=True)
        self._store_timestamp = -1
        self._store = None
        self._refresh()

    def _refresh(self):
        current_timestamp = self.CREDENTIALS_STORE.stat().st_mtime
        if self._store_timestamp < current_timestamp:
            self._store = toml.loads(self.CREDENTIALS_STORE.read_text())
            self._store_timestamp = current_timestamp

    def _save(self):
        self.CREDENTIALS_STORE.write_text(toml.dumps(self._store))
        self._store_timestamp = self.CREDENTIALS_STORE.stat().st_mtime

    def _get(self, label):
        return self._store[label]

    def get(self, label):
        self._refresh()
        d = self._get(label)
        return d["url"], d["token"]

    def _set(self, label, url, token):
        if not url.startswith("http"):
            url = f"https://{url}"
        self._store[label] = {"url": url, "token": token}
        self._save()

    def set(self, label, url, token):
        self._refresh()
        self._set(label, url, token)

    def remove(self, label):
        self._refresh()
        if label in self._store:
            del self._store[label]
        self._save()


def _get_env_var(name):
    try:
        return os.environ[name]
    except KeyError:
        raise encapsia_api.EncapsiaApiError(
            f"Environment variable {name} does not exist!"
        )


def discover_credentials(host=None):
    """Return (url, token) or raise EncapsiaApiError."""
    if not host:
        host = os.environ.get("ENCAPSIA_HOST")
    if host:
        store = CredentialsStore()
        try:
            url, token = store.get(host)
        except KeyError:
            raise encapsia_api.EncapsiaApiError(
                f"Cannot find entry for '{host}' in encapsia credentials file."
            )
    else:
        url, token = _get_env_var("ENCAPSIA_URL"), _get_env_var("ENCAPSIA_TOKEN")
    return url, token
