"""Offline smoke test: exercises auth, inventory and reports against the fake
Supabase client in ``fake_supabase.py`` using Streamlit's AppTest.

Run: python tests_smoke.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from fake_supabase import FAKE, ITEMS, TXNS, USERS  # noqa: E402,F401  (patching side effect)

# ---------------------------------------------------------------- fake client

# ------------------------------------------------------------------- test
failures: list[str] = []


def check(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        failures.append(msg)


at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
at.run()

# Force the fake client for every rerun (app module imports happen per run)
at.session_state["logged_in"] = False
at.run()
check(not at.exception, f"app ran without exception {[e.value for e in at.exception]}")
check(any("Concord ChemTrack" in m.value for m in at.markdown), "login card branding rendered")
check(len(at.text_input) >= 2, "login username/password inputs present")

# wrong password
at.text_input(key="login_username").set_value("tester")
at.text_input(key="login_password").set_value("bad")
at.button[0].click().run()
check(any("Invalid" in e.value for e in at.error), "wrong password rejected")

# correct password
at.text_input(key="login_username").set_value("tester")
at.text_input(key="login_password").set_value("secret1")
at.button[0].click().run()
check(at.session_state["logged_in"] is True, "successful login sets logged_in")
check(at.session_state["username"] == "tester", "username stored in session state")
check(not at.exception, f"dashboard ran without exception {[e.value for e in at.exception]}")

# navigate to Report and back
at.session_state["nav"] = "Report"
at.run()
check(not at.exception, f"report page ran without exception {[e.value for e in at.exception]}")
check(any("Report" in m.value for m in at.markdown), "report header rendered")

at.session_state["nav"] = "Chemical Add_on"
at.run()
check(not at.exception, f"inventory page ran without exception {[e.value for e in at.exception]}")

# logout
at.session_state["logged_in"] = False
at.run()
check(any("Concord ChemTrack" in m.value for m in at.markdown), "returns to login after logout")

# ---------------------------------------------------------- registration
at.session_state["auth_view"] = "register"
at.run()
at.text_input(key="reg_username").set_value("newuser")
at.text_input(key="reg_password").set_value("abc12345")
at.text_input(key="reg_confirm").set_value("abc12345")
at.button[0].click().run()
check(any(u["username"] == "newuser" for u in USERS), "registration inserts into users table")
check(USERS[-1]["password"].startswith("pbkdf2_sha256$"), "password stored hashed, not plain text")
check(at.session_state["auth_view"] == "login", "registration returns to login view")

# duplicate username is rejected
at.session_state["auth_view"] = "register"
at.run()
at.text_input(key="reg_username").set_value("newuser")
at.text_input(key="reg_password").set_value("abc12345")
at.text_input(key="reg_confirm").set_value("abc12345")
at.button[0].click().run()
check(any("already taken" in e.value for e in at.error), "duplicate username rejected")

# --------------------------------------------------- stock entry insert
at.session_state["auth_view"] = "login"
at.session_state["logged_in"] = True
at.session_state["username"] = "tester"
at.session_state["nav"] = "Chemical Add_on"
at.run()
before = len(TXNS)
# number_input[0] = stock-entry quantity; form_submit_button[0] = "Save stock entry"
at.number_input[0].set_value(5.0)
at.form_submit_button[0].click().run()
check(len(TXNS) == before + 1, "stock entry inserts a transaction row")
check(TXNS[-1].get("created_by") == "tester", "transaction records the logged-in user")
check(not at.exception, f"post-save rerun clean {[e.value for e in at.exception]}")

print("\nRESULT:", "ALL CHECKS PASSED" if not failures else f"{len(failures)} FAILURE(S)")
sys.exit(1 if failures else 0)
