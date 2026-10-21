"""In-memory fake Supabase client for offline testing / visual QA.

Importing this module patches ``src.config`` so every Streamlit rerun talks to
an in-memory database instead of the network. Data lists (``USERS``, ``ITEMS``,
``TXNS``) are module-level so tests can assert on inserted rows.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.auth as auth  # noqa: E402
import src.config as cfg  # noqa: E402

# ------------------------------------------------------------------ fixtures
ITEMS = [{
    "id": 1, "item_code": "CFC-0001", "name": "Toluene", "category": "Solvent",
    "unit": "L", "supplier": "SL Chemicals", "reorder_level": 10, "opening_qty": 50,
    "notes": None, "created_by": "tester", "created_at": "2026-01-01",
}]
TXNS = [
    {"id": 1, "item_id": 1, "txn_type": "OUT", "quantity": 45, "unit": "L", "batch_no": "B1",
     "supplier": None, "issued_to": "Moulding", "reference": "REQ-1", "remarks": None,
     "txn_date": "2026-10-01", "created_by": "tester", "created_at": "2026-10-01"},
]
USERS = [{"id": "u1", "username": "tester", "password": auth.hash_password("secret1"),
          "created_at": "2026-01-01"}]

# Long enough to pass the placeholder heuristic in config.credentials_look_valid.
SECRETS = {"SUPABASE_URL": "https://fake.supabase.co",
           "SUPABASE_KEY": "fake-service-role-key-0123456789abcdef"}


# ------------------------------------------------------------------- client
class Resp:
    def __init__(self, data):
        self.data = data


class Query:
    def __init__(self, rows):
        self.rows = rows
        self._filters: list[tuple[str, object]] = []
        self._mode = "select"
        self._payload = None
        self._select = "*"
        self._limit: int | None = None

    # ---- builder API -----------------------------------------------------
    def select(self, *args, **kwargs):
        self._mode = "select"
        self._select = args[0] if args and isinstance(args[0], str) else "*"
        return self

    def insert(self, payload):
        self._mode, self._payload = "insert", payload
        return self

    def update(self, payload):
        self._mode, self._payload = "update", payload
        return self

    def order(self, *a, **k):
        if self._mode == "select" and a:
            key = a[0]
            self.rows = sorted(self.rows, key=lambda r: (r.get(key) is None, str(r.get(key))),
                               reverse=bool(k.get("desc")))
        return self

    def limit(self, n):
        self._limit = n
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def gte(self, col, val):
        self._filters.append((col, (">=", val)))
        return self

    def lte(self, col, val):
        self._filters.append((col, ("<=", val)))
        return self

    # ---- execution -------------------------------------------------------
    def _match(self, row) -> bool:
        for col, val in self._filters:
            if isinstance(val, tuple):
                op, bound = val
                value = row.get(col)
                if value is None or not (value >= bound if op == ">=" else value <= bound):
                    return False
            elif row.get(col) != val:
                return False
        return True

    def execute(self):
        if self._mode == "insert":
            row = dict(self._payload)
            row.setdefault("id", len(self.rows) + 1)
            self.rows.append(row)
            return Resp([row])
        if self._mode == "update":
            for row in self.rows:
                if self._match(row):
                    row.update(self._payload)
            return Resp([])
        rows = [r for r in self.rows if self._match(r)]
        if self._select != "*":
            cols = [c.strip() for c in self._select.split(",")]
            rows = [{c: r.get(c) for c in cols} for r in rows]
        if self._limit is not None:
            rows = rows[: self._limit]
        return Resp(rows)


class FakeClient:
    def __init__(self):
        self.tables = {"users": USERS, "chemical_items": ITEMS,
                       "stock_transactions": TXNS, "chemical_categories": []}

    def table(self, name):
        return Query(self.tables.setdefault(name, []))


FAKE = FakeClient()

# Patch configuration so every rerun resolves to the fake backend.
cfg.create_client = lambda *a, **k: FAKE
cfg._secret = lambda name: SECRETS.get(name)
