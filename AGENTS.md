
# Code Quality Standards (Ruff)

## Formatting Rules

- **Line length**: 100 chars (enforced in `pyproject.toml`)
- **Quotes**: Double quotes only
- **Target**: Python 3.11+
- **Pre-commit**: Run `make format` before every commit
- **Cross-platform**: Ensure all code works on both Windows and Linux (use `pathlib.Path`, avoid shell-specific commands)

## Per-File Ignores

- `__init__.py`: Ignores `F401` (unused imports are acceptable for package exports)
- `schemas/gpt_schema.py`: Ignores `N815` (camelCase allowed to match JSON field names)

## Development Commands

```bash
make lint       # Check code style (non-destructive)
make format     # Auto-fix + format (idempotent, safe to run repeatedly)
```

## Best Practices

1. Always run `make format` before committing
2. Fix lint errors before running the app (enforced by `make check-and-run`)
3. Keep code idiomatic to Python 3.11+ (use type hints, modern syntax)
4. Maintain consistency with existing codebase patterns

---

# Documentation notes

- Do not create a new markdown file for summary documentation on new features.
- Write the concise documentation by updating the README.md file instead.

---

# Streamlit Development Guidelines

## Chart Width Configuration

### General Streamlit Charts
For most Streamlit chart components, use `width="stretch"` instead of the deprecated `use_container_width=True`.

**Correct:**
```python
st.line_chart(data, width="stretch")
st.bar_chart(data, width="stretch")
```

**Incorrect (deprecated):**
```python
st.line_chart(data, use_container_width=True)
st.bar_chart(data, use_container_width=True)
```

### Plotly Charts (st.plotly_chart)
For `st.plotly_chart()` specifically, use the `config` parameter to specify Plotly configuration options instead of width parameters.

**Correct:**
```python
st.plotly_chart(fig, config={"responsive": True})
```

**Incorrect:**
```python
st.plotly_chart(fig, width="stretch")  # Deprecated
st.plotly_chart(fig, use_container_width=True)  # Deprecated
```

### Why This Matters
- `use_container_width=True` is deprecated across Streamlit components
- `width="stretch"` is the modern approach for general charts
- `st.plotly_chart()` uses Plotly's native configuration system via the `config` parameter
- Following these guidelines avoids deprecation warnings and ensures future compatibility

## Semantic Headers with st.subheader()

Use `st.subheader()` for all section headers instead of `st.markdown("### XXXXXXX")`.

**Correct:**
```python
st.subheader("Section Title")
st.subheader("Field Configuration")
```

**Incorrect (deprecated):**
```python
st.markdown("### Section Title")
st.markdown("### Field Configuration")
```

### Why This Matters
- `st.subheader()` is the semantic Streamlit component designed for headers
- `st.markdown("### ...")` is a workaround that doesn't leverage Streamlit's styling system
- Using semantic components ensures consistency, better accessibility, and proper theme support
- Streamlit components adapt to your app's configured theme automatically

---

# VERY IMPORTANT: Do not duplicate instructions

- Do not reuse, copy or duplicate the instructions above here in AGENTS.md for copilot-instructions.md

---

# Project Best Practices (Learned)

## Navigation & Imports
- Use `helpers/utils.py` for shared helpers (e.g., `render_sidebar`). Import directly: `from helpers.utils import render_sidebar`.
- Use `helpers/speech_personal_voice.py` for Personal Voice utilities. Import directly: `from helpers.speech_personal_voice import PersonalVoiceConfig`.
- Keep sidebar links accurate and minimal: `app.py`, `pages/pg1_Voice_Gallery.py`, `pages/pg3_Pricing.py`.
- Ensure `pages/` files are named and placed correctly for Streamlit multi-page discovery.
- Call `st.set_page_config(...)` once and before any other Streamlit calls (centralize in `render_sidebar` or the main app).

## Data & Config
- Externalize static data (e.g., voices) into `inputs/*.json` and load via a cached loader (`@lru_cache`) with validation and logging.
- Keep secrets in environment variables (`AZURE_SPEECH_REGION`, `AZURE_SPEECH_KEY`), never hardcode.

## Observability
- Use module-level loggers (`logger = logging.getLogger(__name__)`).
- Log key actions and outcomes (data loads, filter counts, preview success/failure).

## Typing & Lint
- Prefer built-in generics (`list`, `dict`) over `typing.List`/`typing.Dict`.
- Run `make lint` (Ruff) and `make format` before commits.
