import unittest

from encapsia_api import credentials


class TestCredentialStore(unittest.TestCase):
    def setUp(self):
        self._existing = credentials.CredentialsStore.CREDENTIALS_STORE
        credentials.CredentialsStore.CREDENTIALS_STORE = (
            self._existing.parent / "test-credentials.toml"
        )

    def tearDown(self):
        credentials.CredentialsStore.CREDENTIALS_STORE.unlink()
        credentials.CredentialsStore.CREDENTIALS_STORE = self._existing

    def test_starts_empty(self):
        store = credentials.CredentialsStore()
        self.assertEqual(len(store.get_labels()), 0)

    def test_not_in(self):
        store = credentials.CredentialsStore()
        with self.assertRaises(KeyError):
            store.get("does-not-exist")

    def test_set_and_get(self):
        store = credentials.CredentialsStore()
        store.set("foo", "https://a.b.c", "a-token")
        url, token = store.get("foo")
        self.assertEqual(url, "https://a.b.c")
        self.assertEqual(token, "a-token")

    def test_modify(self):
        store = credentials.CredentialsStore()
        store.set("foo", "https://a.b.c", "a-token")
        store.set("foo", "https://x.y.z", "a-different-token")
        url, token = store.get("foo")
        self.assertEqual(url, "https://x.y.z")
        self.assertEqual(token, "a-different-token")

    def test_can_remove_non_existing(self):
        store = credentials.CredentialsStore()
        store.remove("does-not-exist")

    def test_can_remove_existing(self):
        store = credentials.CredentialsStore()
        store.set("foo", "https://a.b.c", "a-token")
        store.get("foo")  # Does not raise
        store.remove("foo")
        with self.assertRaises(KeyError):
            store.get("foo")  # Raises

    def test_can_get_labels(self):
        store = credentials.CredentialsStore()
        store.set("foo", "https://a.b.c", "a-token")
        store.set("bar", "https://a.b.c", "a-token")
        self.assertEqual(set(store.get_labels()), set(["foo", "bar"]))

    def test_can_remove_from_get_labels(self):
        store = credentials.CredentialsStore()
        store.set("foo", "https://a.b.c", "a-token")
        store.set("bar", "https://a.b.c", "a-token")
        self.assertEqual(set(store.get_labels()), set(["foo", "bar"]))
        store.remove("foo")
        self.assertEqual(set(store.get_labels()), set(["bar"]))
        store.remove("bar")
        self.assertEqual(len(store.get_labels()), 0)

    def test_can_clear_token(self):
        store = credentials.CredentialsStore()
        store.set("foo", "https://a.b.c", "a-token")
        store.clear_token("foo")
        with self.assertRaises(KeyError):
            # By default it now doesn't exist
            store.get("foo")
        # But we can get it if we ask specifically
        url, token = store.get("foo", include_cleared_tokens=True)
        self.assertEqual(url, "https://a.b.c")
        self.assertEqual(token, "")

    def test_can_get_cleared_token_entries_from_get_labels(self):
        store = credentials.CredentialsStore()
        store.set("foo", "https://a.b.c", "a-token")
        store.clear_token("foo")
        # By default, entries with cleared token are not actually present.
        self.assertEqual(len(store.get_labels()), 0)
        # But you can get them too if you ask nicely.
        self.assertEqual(len(store.get_labels(include_cleared_tokens=True)), 1)
        self.assertEqual(
            set(store.get_labels(include_cleared_tokens=True)), set(["foo"])
        )
