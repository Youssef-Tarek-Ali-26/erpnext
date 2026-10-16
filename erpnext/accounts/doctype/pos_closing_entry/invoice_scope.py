# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Server-only extension of POS invoice selection and session membership.

One installed app may register ``pos_closing_invoice_scope``. The three modes
are ``select_invoices``, ``validate_invoice`` and ``validate_cashier``. Selection
returns document names, never SQL, a query object or a client callback. Validation
must return exactly True or raise. No hook preserves native cashier ownership.
"""

import frappe
from frappe import _


def _call_scope(mode, **context):
	hooks = frappe.get_hooks("pos_closing_invoice_scope")
	if not hooks:
		return False, None
	if len(hooks) != 1:
		frappe.throw(_("Only one POS closing invoice scope hook may be configured."))
	return True, frappe.get_attr(hooks[0])(mode=mode, **context)


def select_invoice_names(*, invoice_doctype, user, pos_profile, start, end, pos_opening_entry):
	configured, names = _call_scope(
		"select_invoices", invoice_doctype=invoice_doctype, user=user,
		pos_profile=pos_profile, start=start, end=end, pos_opening_entry=pos_opening_entry,
	)
	if not configured:
		return None
	if (not isinstance(names, (list, tuple)) or any(not isinstance(name, str) or not name for name in names)
		or len(set(names)) != len(names)):
		frappe.throw(_("The POS closing invoice scope must return unique invoice names."))
	return names


def validate_invoice_membership(*, closing, invoice_doctype, invoice_name):
	configured, accepted = _call_scope(
		"validate_invoice", closing=closing, invoice_doctype=invoice_doctype, invoice_name=invoice_name,
	)
	if configured and accepted is not True:
		frappe.throw(_("The invoice is outside this POS closing's scope."))
	return configured


def validate_cashier_membership(opening):
	configured, accepted = _call_scope("validate_cashier", opening=opening)
	if configured and accepted is not True:
		frappe.throw(_("The cashier is already assigned to another POS session."))
	return configured
