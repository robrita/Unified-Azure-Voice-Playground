# Azure Personal Voice Playground - AI Agent Instructions

## Project Overview

A Streamlit-based playground for testing Azure Speech Service's Personal Voice feature, built with **Streamlit 1.50.0**, connecting to Azure AI services via pluggable handlers. Create custom text-to-speech voices using audio samples, manage speaker profiles, and synthesize speech with personalized voices.

**Tech Stack**: Python 3.11+ | Streamlit | uv/pyproject.toml | Azure AI Services | Ruff | pytest (100% coverage)

## Architecture

### Core Components
- **`app.py`**: Main Streamlit app with async parallel extraction (`asyncio.run`)
- **`handlers/`**: Service adapters following duck-typed contract (no base class)
- **`utils.py`**: Shared utilities (`save_extraction_to_json`, `keep_state`, `render_sidebar`)
- **`schemas/`**: Pydantic models for structured extraction (e.g., `gpt_schema.py`)
- **`pages/`**: Streamlit multi-page components (Schema Builder, Form PreFill, Pricing)

### Handler Contract (Duck-Typed Pattern)
Every handler in `handlers/` must implement:

```python
class ServiceHandler:
    def __init__(self, service_name: str = None):
        self.service_name = service_name
        self.endpoint = os.environ.get("AZURE_*_ENDPOINT")
        self.key = os.environ.get("AZURE_*_KEY")
        # Lazy init: only create client if credentials exist
        
    def extract(self, uploaded_file) -> dict[str, Any]:
        """Returns {'service': name, 'error'?: msg, ...data}"""
        start_time = time.time()
        try:
            # Process file, return results with processing_time
        except Exception as e:
            return {"service": self.service_name, "error": str(e)}
```

**Critical Rules**:
- Always return `dict[str, Any]` (never raise exceptions)
- Include `'service'` key in all responses
- Return `{'error': str}` on failure for graceful UI handling
- Track `processing_time` for performance metrics
- See `handlers/document_intelligence.py` as reference implementation

### Data Flow
1. **Upload**: User selects files + services in `app.py` → stored in `st.session_state`
2. **Parallel Extraction**: `process_file_with_services_async()` runs handlers concurrently via `asyncio.gather()`
3. **Normalization**: `save_extraction_to_json()` writes to `outputs/extract_results.json` (deduplicates by `file_name + service_name`)
4. **Analysis**: Tab 2 loads JSON, generates tables/charts with Plotly

## Development Workflow

### Commands (Makefile + uv)
```bash
make install       # Install deps (uv sync)
make format        # Ruff auto-fix + format (REQUIRED before commit)
make lint          # Check code style only
make check-and-run # Lint gate → run app
make test-unit     # Fast tests (no Azure calls)
make test-cov      # Generate htmlcov/index.html
uv run streamlit run app.py  # Direct app launch
```

**Pre-commit Rule**: Always run `make format` (enforced by Ruff config in `pyproject.toml`)

### Testing Strategy
- **Unit Tests** (`-m "not integration"`): Mock Azure clients, fast, isolated
- **Integration Tests** (`-m integration`): Require `.env` credentials
- **Fixtures**: Defined in `tests/conftest.py` (`sample_image_file`, `mock_env_vars`, etc.)
- **Coverage Target**: 100% (enforced by `make test-cov`)

Example test pattern:
```python
@pytest.mark.unit
def test_handler_extract(mock_pdf_file, mock_env_vars):
    handler = ServiceHandler("Test-Service")
    result = handler.extract(mock_pdf_file)
    assert "service" in result
    assert "error" not in result  # Success case
```

## Key Conventions

### Session State Persistence
```python
# Session state persistence across pages
from utils import keep_state
keep_state(valid_files, "valid_files")  # Survives page navigation
```

### JSON Output Standardization
Always use utility function to maintain schema consistency:

```python
from utils import save_extraction_to_json
save_extraction_to_json(
    file_name="doc.pdf",
    service_name="GPT-4.1-Vision",  # Must be in VALID_SERVICE_NAMES
    pages_count=1,
    fields={"tin": {"content": "123-456-789", "confidence": 0.98}},
    overall_confidence=0.95,
    processing_time=2.5
)
```

**Schema** (in `outputs/extract_results.json`):
```json
{
  "results": [
    {
      "file_name": "doc.pdf",
      "service_name": "GPT-4.1-Vision",
      "pages_count": 1,
      "document_confidence": 0.950,
      "processing_time": 2.500,
      "fields": [
        {"name": "tin", "value": "123-456-789", "confidence": 0.980}
      ]
    }
  ]
}
```

### Environment Variables
All Azure credentials loaded from `.env` (not committed). Services gracefully degrade if credentials missing:

```python
# Pattern in handlers
self.client = None
if self.endpoint and self.key:
    self.client = AzureClient(...)
else:
    logger.error(f"Missing credentials for {service_name}")
```

## Adding a New Service

**Checklist**:
1. ✅ Create `handlers/new_service.py` implementing contract
2. ✅ Add env vars to `.env.example` and README
3. ✅ Import in `handlers/__init__.py` and `app.py`
4. ✅ Add checkbox in `app.py` UI (line ~205)
5. ✅ Add to `VALID_SERVICE_NAMES` in `utils.py`
6. ✅ Write unit tests in `tests/test_handlers.py` with `@pytest.mark.unit`
7. ✅ Run `make format && make test-unit`

**Reference**: See `.github/instructions/adding-services.instructions.md` for detailed guide

## Project-Specific Quirks

### Async Extraction Pattern
`app.py` uses `asyncio.gather()` to run multiple handlers in parallel per file:

```python
async def process_file_with_services_async(file, selected_services):
    tasks = [extract_with_service_async(svc_name, svc_class, file) 
             for svc_name, svc_class in selected_services]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Returns: {"ServiceName": result_dict, ...}
```

**Why**: Reduces total processing time from serial ~15s to parallel ~5s for 3 services.

### Service Names Must Match
The tuple in `app.py` must match `VALID_SERVICE_NAMES` in `utils.py`:

```python
# app.py
selected_services.append(("GPT-4.1-Vision", GPTForVision))  # Key name

# utils.py
VALID_SERVICE_NAMES = {"GPT-4.1-Vision", ...}  # Must contain exact match
```

Mismatch causes validation error in `save_extraction_to_json()`.

### Pydantic Schema Convention
Use `Field(None, description=...)` for all optional fields. CamelCase allowed in `schemas/gpt_schema.py` to match Azure API responses (Ruff N815 ignored).

### Logging Configuration
Custom millisecond formatter in `app.py`:

```python
class MillisecondFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        # Formats as: 2024-01-15 10:30:45.123
```

Suppress verbose Azure SDK logs:
```python
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
```

## Common Pitfalls

1. **Hardcoding service names**: Always pass `service_name` parameter to handlers
2. **Missing error handling**: Handlers must return `{'error': str}`, never raise
3. **Session state loss**: Use `keep_state()` for data that survives page navigation

## Files to Check Before Changes

| Change Type | Files to Review |
|-------------|-----------------|
| Add service | `handlers/__init__.py`, `app.py` (checkboxes), `utils.py` (VALID_SERVICES), tests |
| Modify extraction | Handler file, `utils.py` (JSON schema), tests |
| UI changes | `app.py`, `style.css`, `pages/*.py` |
| Testing | `conftest.py` (fixtures), `pytest.ini` (markers) |
| Dependencies | `pyproject.toml` (both deps + dev-dependencies) |

## Quick Reference

```bash
# Essential Commands
make format          # Fix all style issues (idempotent)
make test-unit       # Fast feedback loop (no Azure)
make check-and-run   # Validate + launch app

# Debugging
uv run pytest tests/test_handlers.py::TestClassName::test_method -v -s
uv run ruff check --diff .  # Preview changes without applying

# Coverage
make test-cov && start htmlcov/index.html  # Windows
```

## Further Reading

- `.github/instructions/handler-pattern.instructions.md` - Handler implementation contract
- `.github/instructions/testing.instructions.md` - Testing strategy and fixtures
- `AGENTS.md` - Code quality standards (Ruff), Streamlit patterns, and documentation guidelines
- `README.md` - Complete setup and usage guide
