---
agent: agent
---
# Create New Streamlit Page (Generic)

## Goal
Create a new Streamlit page for this repo that:
- Matches existing app UI/architecture patterns.
- Encapsulates any new feature logic behind small helper modules.
- Persists any user configuration locally (if needed) without committing secrets.
- Includes unit tests (mocked, no live cloud calls).

## Inputs (fill these in)
- Page filename: `pages/pgX_<Page_Name>.py`
- Page title + purpose: `<what does this page do?>`
- Feature requirements (bullets):
  - `<requirement 1>`
  - `<requirement 2>`
- Any external services/APIs used:
  - `<service name>` + `<SDK/REST>` + `<auth method>`
- Data persistence needs (if any):
  - `<what to persist?>` + `<where?>` + `<security constraints>`

## Requirements

### A) New page
- Add a new Streamlit page under `pages/` with the filename above.
- Follow existing page patterns:
  - Call `render_sidebar()` at the top of `main()`.
  - Use `st.subheader()` for section headings (avoid `st.markdown("### ...")`).
  - Prefer modern Streamlit width usage (`width="stretch"` where supported).
  - Use `st.session_state` to persist UI state across reruns.

### B) Navigation / sidebar
- Ensure the page is discoverable from the app’s sidebar.
  - If the repo uses `st.page_link(...)`, add a link for the new page.

### C) Feature logic placement
- Keep non-UI logic out of the page file.
- Create helper module(s) for the feature in an appropriate location, for example:
  - `utils/<feature_name>.py` (preferred for shared helpers)
  - `handlers/<service_name>.py` (only if it fits the handler contract and is used in the extraction flow)

### D) Local persistence (optional)
If the page needs to persist configuration/results locally:
- Store it under `outputs/`.
- Add the relevant output files to `.gitignore` (especially if they contain secrets).
- Never commit credentials.

### E) External service integration (optional)
If the page calls an external service/API:
- Support both “SDK” and “REST” styles if applicable.
- Implement robust error handling:
  - Do not crash the UI.
  - Return structured results (e.g., dicts with `ok: bool`, `error: str`, and optional details).
- If the service is asynchronous / long-running:
  - Provide optional polling/status display.

### F) Dependencies
- Add any required dependencies to `pyproject.toml`.
- Keep dependencies minimal.

### G) Tests
- Add unit tests under `tests/` for any new helper modules.
- Unit tests must not call external services:
  - Mock SDK clients.
  - For REST integrations, use a fake `requests`-like client.

## Constraints
- Follow repo style: Ruff formatting, double quotes, Python 3.11+.
- Do not add new markdown documentation files; update `README.md` only if needed.
- Cross-platform: use `pathlib.Path`, avoid shell-specific assumptions.

## Success criteria
- The new page loads in Streamlit without errors.
- Core user workflows work end-to-end.
- `make format` is clean.
- `make test-unit` passes.

## Validation commands
- `make format`
- `make test-unit`
- `uv run streamlit run app.py`