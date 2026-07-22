"""Unit tests for Role-Based Access Control (RBAC) filtering logic."""

import unittest
from backend.api.middleware.rbac import (
    user_can_access,
    get_qdrant_access_filter,
    get_qdrant_group_filter,
)


class TestRBACFiltering(unittest.TestCase):

    def test_user_can_access_employee(self):
        """Employee role should access 'general' but NOT 'leadership'."""
        self.assertTrue(user_can_access("employee", "general"))
        self.assertFalse(user_can_access("employee", "leadership"))

    def test_user_can_access_leadership(self):
        """Leadership role should access both 'general' and 'leadership'."""
        self.assertTrue(user_can_access("leadership", "general"))
        self.assertTrue(user_can_access("leadership", "leadership"))

    def test_user_can_access_admin(self):
        """Admin role should access all access levels."""
        self.assertTrue(user_can_access("admin", "general"))
        self.assertTrue(user_can_access("admin", "leadership"))

    def test_qdrant_access_filter(self):
        """Qdrant filter should be None for leadership/admin, 'general' for employee."""
        self.assertIsNone(get_qdrant_access_filter("leadership"))
        self.assertIsNone(get_qdrant_access_filter("admin"))
        self.assertEqual(get_qdrant_access_filter("employee"), "general")
        self.assertEqual(get_qdrant_access_filter("manager"), "general")

    def test_qdrant_group_filter(self):
        """Group filter should return None for 'all' group, or list of user groups."""
        self.assertIsNone(get_qdrant_group_filter(["all"]))
        self.assertEqual(get_qdrant_group_filter(["engineering", "hr"]), ["engineering", "hr"])


if __name__ == "__main__":
    unittest.main()
