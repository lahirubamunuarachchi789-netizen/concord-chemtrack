# Concord ChemTrack 🧪

A responsive Streamlit inventory application for **Concord Footwear (Pvt) Ltd**,
powered by **Supabase**. It manages chemical master items, records stock
entries (IN / OUT / ADJUST) and reports on stock movements.

---

## 1. Quick start

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the app (creates .streamlit/secrets.toml template on first run)
streamlit run app.py
```

## 2. Configure Supabase credentials

The app reads credentials **only** from `st.secrets` (with environment variables
as a fallback). On first run it automatically creates
`.streamlit/secrets.toml` from a template. Fill it in:

```toml
SUPABASE_URL = "https://YOUR-PROJECT-REF.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_ANON_OR_SERVICE_ROLE_KEY"
```

Find both under **Supabase → Project Settings → API**, then refresh the page.

> 🔒 `.streamlit/secrets.toml` is listed in `.gitignore` and must **never** be
> committed. Use `.streamlit/secrets.toml.example` when sharing the project.
> Streamlit Community Cloud users should paste the values into the app's
> *Settings → Secrets* instead of shipping the file.

## 3. Database setup

Your existing `users` table is used for authentication:

| column | type | notes |
|---|---|---|
| `id` | uuid | primary key, default `gen_random_uuid()` |
| `username` | text | unique |
| `password` | text | stores a salted PBKDF2-SHA256 hash |
| `created_at` | timestamptz | default `now()` |

Two extra tables are needed for inventory. Run [`sql/schema.sql`](sql/schema.sql)
once in the Supabase SQL editor. The app detects missing tables and tells you
when to do this.

Passwords are stored as `pbkdf2_sha256$<iterations>$<salt>$<hash>`. Legacy
plain-text rows still authenticate and are upgraded to a hash on next sign-in.

## 4. Project structure

```
app.py                     Streamlit entry point (routing + sidebar)
requirements.txt
.gitignore                 Keeps secrets out of GitHub
.streamlit/
  config.toml              Theme (Navy Blue / White) – no credentials
  secrets.toml.example     Template for local credentials
sql/schema.sql             Required tables / indexes
src/
  config.py                Secrets loading, Supabase client, error mapping
  styles.py                Responsive CSS (mobile-first), navy/white theme
  ui.py                    Headers, KPI tiles, cards, tables, Excel export
  auth.py                  Login + registration, password hashing, session
  inventory.py             "Chemical Add_on" module
  reports.py               "Report" module (filters, summaries, exports)
tests_smoke.py             Offline end-to-end tests (fake Supabase client)
fake_supabase.py           In-memory Supabase stand-in used by the tests
tools_render_static.py     Renders QA screenshots without credentials
```

## 5. Features

**Chemical Add_on**
- KPI overview: master items, total stock, low stock, out of stock
- Record stock entries: receipt (IN), issue (OUT) or adjustment (ADJUST),
  with batch, supplier, reference, issuing department and remarks
- Master item catalogue with search, low-stock filter and Excel export

**Report**
- Date-range, transaction-type and free-text filters
- Transaction log (Excel / CSV export)
- Movement summary per chemical, charts by transaction type and by user
- Current stock position across all items

## 6. Responsive design

The layout is mobile-first: cards, KPI tiles and form fields stack into a single
column on phones, side-by-side columns collapse, and the sidebar shrinks to 86%
viewport width. Navigation stays reachable through Streamlit's normal sidebar
toggle on every screen size.

## 7. Testing

```powershell
python tests_smoke.py        # 18 offline checks: login, register, stock entry, reports
python tools_render_static.py  # writes qa/*.html for visual inspection
```

Both scripts use `fake_supabase.py`, so they never touch your real database.

## 8. Security notes

- Credentials are never hard-coded, logged or committed.
- Session state (`logged_in`, `username`) lives only in the browser session.
- Login errors are deliberately generic ("Invalid username or password").
- Use the Supabase **service role** key only on a trusted internal host; the
  service user that runs the app can bypass Row Level Security, so restrict
  access to the Streamlit instance itself.
