# POS closing invoice scope

Applications can register one server hook in `hooks.py`:

```python
pos_closing_invoice_scope = "my_app.pos.invoice_scope"
```

The callable accepts keyword arguments and handles three explicit modes:

| `mode` | Additional arguments | Required return |
| --- | --- | --- |
| `select_invoices` | `invoice_doctype`, `user`, `pos_profile`, `start`, `end`, `pos_opening_entry` | A list or tuple of unique invoice names |
| `validate_invoice` | `closing` (server Document), `invoice_doctype`, `invoice_name` | Exactly `True`, or raise |
| `validate_cashier` | `opening` (server Document) | Exactly `True`, or raise |

Use this for a shared physical till whose opening cashier differs from its
invoice authors. The application must authorize the caller, verify immutable
session membership and invoice attribution, and enforce its active cashier
assignment invariant. Selection never returns SQL or callbacks. Native date,
profile, submission and consolidation predicates still constrain selection;
native invoice validation, reconciliation and posting still run. Empty
selection means no invoices, while a missing/invalid return fails closed.

With no hook, the original invoice-owner selection, invoice-owner validation,
cashier assignment and profile uniqueness checks remain in effect. Multiple
registered handlers are refused to avoid ambiguous financial scope. The hook
is called only by server code; it is not an RPC or a permission override.
