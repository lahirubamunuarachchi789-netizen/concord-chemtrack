# Deploying Concord ChemTrack

## ⚠️ Vercel cannot host this app

Vercel's Python runtime executes **WSGI/ASGI** applications (FastAPI, Flask,
Django) and looks for a top-level `app` / `application` object in `app.py`
([Vercel: Python runtime](https://vercel.com/docs/functions/runtimes/python)).
Streamlit is not a WSGI/ASGI app — it is a long-running server that keeps a
WebSocket open for every browser session, which Vercel Functions do not provide.

That is what `PYTHON_ENTRYPOINT_NOT_FOUND` reports: no importable `app` object
was found, because a Streamlit app has none. **No `vercel.json` can fix this** —
any configuration file would only change the error, not make the app work.

> If you keep the Vercel project, delete or disconnect it so the failed build
> does not keep notifying you.

## ✅ Recommended: Streamlit Community Cloud (free)

Deploys directly from this GitHub repo, and is the host Streamlit documents for
this purpose ([Streamlit docs](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app)).

1. Go to <https://share.streamlit.io> and sign in with GitHub.
2. **Create app** → *Deploy a public app from GitHub*.
3. Fill in:
   - **Repository:** `lahirubamunuarachchi789-netizen/concord-chemtrack`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. Open **Advanced settings → Secrets** and paste your credentials
   (replace the placeholder values):

   ```toml
   SUPABASE_URL = "https://YOUR-PROJECT-REF.supabase.co"
   SUPABASE_KEY = "YOUR_SUPABASE_ANON_OR_SERVICE_ROLE_KEY"
   ```

   These are stored in Streamlit Cloud's own secret store — not in the repo, and
   not in `.streamlit/secrets.toml` (which stays git-ignored).
5. **Deploy.** First build installs `requirements.txt` and takes a few minutes.

`requirements.txt` and `.streamlit/config.toml` (theme) are detected automatically.

### Private repo?

Streamlit Cloud can deploy private repos if you grant it access during the
GitHub authorization step. Otherwise make the repo public (it contains no
credentials — only the `secrets.toml.example` template).

## Alternatives that support Streamlit

| Host | Notes |
|---|---|
| **Streamlit Community Cloud** | Free, designed for Streamlit, secrets UI, sleep when idle. Best fit. |
| **Render** | Pay-as-you-go web service; start command `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`. |
| **Railway** | Managed deploy; set the same start command, add env vars `SUPABASE_URL` / `SUPABASE_KEY`. |
| **Azure App Service / VPS** | Full control; run the command above behind a reverse proxy. |

On hosts other than Streamlit Cloud, the app also reads `SUPABASE_URL` and
`SUPABASE_KEY` from **environment variables** as a fallback, so you can set them
in the platform's dashboard instead of a secrets file.

## Checklist before going live

- [ ] `sql/schema.sql` has been run once in the Supabase SQL editor.
- [ ] `SUPABASE_URL` / `SUPABASE_KEY` are set in the host's secret store.
- [ ] The `users` table exists and you have at least one account.
- [ ] Prefer an internal/private instance: with the service-role key, anyone who
      can reach the URL can read and write all inventory data.
