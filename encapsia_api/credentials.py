from pathlib import Path

import toml


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
        return d["host"], d["token"]

    def _set(self, label, host, token):
        self._store[label] = {"host": host, "token": token}
        self._save()

    def set(self, label, host, token):
        self._refresh()
        self._set(label, host, token)

    def remove(self, label):
        self._refresh()
        if label in self._store:
            del self._store[label]
        self._save()
