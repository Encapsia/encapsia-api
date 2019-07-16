import collections
import unittest
import unittest.mock

from encapsia_api import rest


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
