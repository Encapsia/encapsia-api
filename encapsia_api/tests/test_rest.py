import collections
import typing
import unittest
import unittest.mock

import requests_mock

from encapsia_api import resilient_request, rest


class TestSystemUserMixin(unittest.TestCase):
    def test_make_system_user_email_from_description(self):
        mixin = rest.SystemUserMixin()
        self.assertEqual(
            "system@a-description.encapsia.com",
            mixin.make_system_user_email_from_description("A Description"),
        )
        self.assertEqual(
            "system@a-b.encapsia.com",
            mixin.make_system_user_email_from_description("a-b"),
        )

    def test_make_system_user_role_name_from_description(self):
        mixin = rest.SystemUserMixin()
        self.assertEqual(
            "System - A description",
            mixin.make_system_user_role_name_from_description("A Description"),
        )
        self.assertEqual(
            "System - Foo", mixin.make_system_user_role_name_from_description("foo")
        )

    def test_add_system_user(self):
        mixin = rest.SystemUserMixin()
        mixin.get_system_users = unittest.mock.Mock(return_value=[])
        mixin.post = unittest.mock.Mock()
        mixin.add_system_user("a description", ["a", "b"], force=False)
        mixin.get_system_users.assert_called()
        mixin.post.assert_has_calls(
            [
                unittest.mock.call(
                    "roles",
                    json=[
                        {
                            "name": "System - A description",
                            "alias": "System - A description",
                            "capabilities": ["a", "b"],
                        }
                    ],
                ),
                unittest.mock.call(
                    "users",
                    json=[
                        {
                            "email": "system@a-description.encapsia.com",
                            "first_name": "System",
                            "last_name": "A description",
                            "role": "System - A description",
                            "enabled": True,
                            "is_site_user": False,
                        }
                    ],
                ),
            ]
        )

    def test_add_system_user_does_nothing_if_already_present(self):
        mixin = rest.SystemUserMixin()
        SystemUser = collections.namedtuple(
            "SystemUser", "email description capabilities"
        )
        mixin.get_system_users = unittest.mock.Mock(
            return_value=[
                SystemUser(
                    "system@a-description.encapsia.com", "A description", ["a", "b"]
                )
            ]
        )
        mixin.post = unittest.mock.Mock()
        mixin.add_system_user("a description", ["a", "b"], force=False)
        mixin.get_system_users.assert_called()
        mixin.post.assert_not_called()

    def test_add_system_user_always_adds_if_forced(self):
        mixin = rest.SystemUserMixin()
        mixin.get_system_users = unittest.mock.Mock(return_value=[])
        mixin.post = unittest.mock.Mock()
        mixin.add_system_user("a description", ["a", "b"], force=True)
        mixin.get_system_users.assert_not_called()
        mixin.post.assert_called()

    def test_get_system_user_by_description(self):
        mixin = rest.SystemUserMixin()
        SystemUser = collections.namedtuple(
            "SystemUser", "email description capabilities"
        )
        the_system_user = SystemUser(
            "system@a-description.encapsia.com", "A description", ["a", "b"]
        )
        mixin.get_system_users = unittest.mock.Mock(return_value=[the_system_user])

        self.assertEqual(
            mixin.get_system_user_by_description("A description"), the_system_user
        )
        self.assertEqual(
            mixin.get_system_user_by_description("a description"), the_system_user
        )
        self.assertEqual(
            mixin.get_system_user_by_description("a different description"), None
        )


class TestHostProperty(unittest.TestCase):
    def test_localhost(self):
        api = rest.EncapsiaApi("localhost", "token")
        self.assertEqual(api.host, "localhost")

    def test_fqdn(self):
        api = rest.EncapsiaApi("my.domain.tld", "token")
        self.assertEqual(api.host, "my.domain.tld")

    def test_url(self):
        api = rest.EncapsiaApi("https://snorri.icethree.com", "token")
        self.assertEqual(api.host, "snorri.icethree.com")


class TestResilientRestAPI(unittest.TestCase):
    API_URL = "https://localhost.icethree.com"
    TEST_URL = "https://localhost.icethree.com/v1/whoami"
    RESPONSE: typing.ClassVar[typing.Dict[str, typing.Any]] = {
        "status": "ok",
        "result": {
            "id": 1,
            "name": "Root Superuser",
            "email": "system@root.encapsia.com",
            "capabilities": ["superuser"],
            "expires_at": "2021-09-28T13:24:21.745065+00:00",
            "issued_at": "2021-09-27T13:24:21.745065+00:00",
            "device": None,
            "notification_token": None,
            "role": None,
            "site_id": "",
            "role_alias": None,
            "token": "token",
        },
    }

    def setUp(self):
        self.api = rest.EncapsiaApi(self.API_URL, "token")

    def test_call_once_if_success(self):
        with requests_mock.Mocker() as m:
            m.get(self.TEST_URL, json=self.RESPONSE)
            result = self.api.whoami()
            self.assertEqual(m.call_count, 1)
            self.assertEqual(result, self.RESPONSE["result"])

    def test_default_timeout_is_set(self):
        with requests_mock.Mocker() as m:
            m.get(self.TEST_URL, json=self.RESPONSE)
            self.api.whoami()
            self.assertEqual(m.last_request.timeout, resilient_request.DEFAULT_TIMEOUT)

    def test_custom_timeout_is_set(self):
        with requests_mock.Mocker() as m:
            m.get(self.TEST_URL, json=self.RESPONSE)
            self.api.replace(timeout=10).whoami()
            self.assertEqual(m.last_request.timeout, 10)

    def test_replace_timeout(self):
        api2 = self.api.replace(timeout=99)
        self.assertEqual(api2._timeout, 99)
        self.assertIsNot(api2, self.api)
        self.assertEqual(api2._retries, self.api._retries)
        self.assertEqual(api2._retry_delay, self.api._retry_delay)

    def test_replace_all(self):
        api2 = self.api.replace(timeout=99, retries=88, retry_delay=77)
        self.assertIsNot(api2, self.api)
        self.assertEqual(api2._timeout, 99)
        self.assertEqual(api2._retries, 88)
        self.assertEqual(api2._retry_delay, 77)

    def test_resilient_request_is_called(self):
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.RESPONSE
        with unittest.mock.patch.object(
            rest, "resilient_request", return_value=mock_response
        ) as mock_rr:
            self.api.whoami()
            mock_rr.assert_called()
