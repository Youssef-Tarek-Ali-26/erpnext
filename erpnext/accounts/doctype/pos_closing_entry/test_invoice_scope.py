# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.accounts.doctype.pos_closing_entry.invoice_scope import (
	select_invoice_names, validate_cashier_membership, validate_invoice_membership,
)
from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import build_invoice_query
from erpnext.tests.utils import ERPNextTestSuite


class TestInvoiceScope(ERPNextTestSuite):
	def test_no_hook_native_cashier_and_profile_assignment_with_real_opening(self):
		from erpnext.accounts.doctype.pos_closing_entry.test_pos_closing_entry import init_user_and_profile
		from erpnext.accounts.doctype.pos_opening_entry.pos_opening_entry import POSOpeningEntry
		from erpnext.accounts.doctype.pos_opening_entry.test_pos_opening_entry import create_opening_entry

		previous_user = frappe.session.user
		self.addCleanup(frappe.set_user, previous_user)
		user, profile = init_user_and_profile()
		original_get_hooks = frappe.get_hooks
		def without_scope(hook=None, *args, **kwargs):
			return [] if hook == "pos_closing_invoice_scope" else original_get_hooks(hook, *args, **kwargs)
		with patch("frappe.get_hooks", side_effect=without_scope):
			opening = create_opening_entry(profile, user.name, get_obj=True)
			candidate = frappe.new_doc("POS Opening Entry")
			candidate.user, candidate.pos_profile = user.name, profile.name
			with self.assertRaises(frappe.ValidationError):
				POSOpeningEntry.check_user_already_assigned(candidate)
			with self.assertRaises(frappe.ValidationError):
				POSOpeningEntry.check_open_pos_exists(candidate)
			self.assertEqual(opening.user, user.name)

	def test_no_hook_preserves_native_ownership_query_and_membership(self):
		with patch("frappe.get_hooks", return_value=[]):
			self.assertIsNone(select_invoice_names(invoice_doctype="POS Invoice", user="cashier",
				pos_profile="profile", start="2026-01-01", end="2026-01-02", pos_opening_entry="opening"))
			self.assertFalse(validate_cashier_membership(frappe._dict(user="cashier")))
			self.assertFalse(validate_invoice_membership(closing=frappe._dict(user="cashier"),
				invoice_doctype="POS Invoice", invoice_name="invoice"))
			query = build_invoice_query("POS Invoice", "cashier", "profile", "2026-01-01", "2026-01-02")
			self.assertIn("owner", str(query))
			self.assertIn("cashier", str(query))

	def test_one_server_hook_handles_all_modes_and_names_are_query_values(self):
		calls = []
		def handler(*, mode, **context):
			calls.append((mode, context))
			return ["invoice'quoted"] if mode == "select_invoices" else True
		with patch("frappe.get_hooks", return_value=["test.handler"]), patch("frappe.get_attr", return_value=handler):
			query = build_invoice_query("POS Invoice", "cashier", "profile", "2026-01-01", "2026-01-02", pos_opening_entry="opening")
			self.assertNotIn("`owner`", str(query))
			self.assertTrue(validate_cashier_membership(frappe._dict(user="cashier")))
			self.assertTrue(validate_invoice_membership(closing=frappe._dict(user="cashier"),
				invoice_doctype="POS Invoice", invoice_name="invoice"))
		self.assertEqual([mode for mode, _context in calls], ["select_invoices", "validate_cashier", "validate_invoice"])
		self.assertEqual(calls[0][1]["pos_opening_entry"], "opening")

	def test_invalid_selection_or_membership_fails_closed(self):
		for result in (None, "select * from invoice", {}, ["invoice", "invoice"], [None]):
			with self.subTest(result=result), patch("frappe.get_hooks", return_value=["test.handler"]), patch("frappe.get_attr", return_value=lambda **_kw: result):
				with self.assertRaises(frappe.ValidationError):
					select_invoice_names(invoice_doctype="POS Invoice", user="cashier", pos_profile="profile",
						start="2026-01-01", end="2026-01-02", pos_opening_entry="opening")
		for result in (None, False, 1, "true"):
			with self.subTest(result=result), patch("frappe.get_hooks", return_value=["test.handler"]), patch("frappe.get_attr", return_value=lambda **_kw: result):
				with self.assertRaises(frappe.ValidationError):
					validate_cashier_membership(frappe._dict(user="cashier"))
		with patch("frappe.get_hooks", return_value=["one.handler", "two.handler"]):
			with self.assertRaises(frappe.ValidationError):
				validate_cashier_membership(frappe._dict(user="cashier"))
