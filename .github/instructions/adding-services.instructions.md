---
description: Step-by-step guide for adding new voice playground services
applyTo: 'handlers/*.py, app.py, tests/*.py'
---

# Adding a New Service

Follow these steps to add a new voice playground service:

## 1. Create Handler
Create `handlers/new_service.py` with class implementing:
- `__init__(service_name: str = None)`: Initialize with service name and credentials
- `extract(uploaded_file) -> dict[str, Any]`: Main extraction logic

**Template:**
```python
class NewService:
    def __init__(self, service_name: str = None):
        self.service_name = service_name or "New Service"
        self.endpoint = os.environ.get("AZURE_NEW_SERVICE_ENDPOINT")
        self.key = os.environ.get("AZURE_NEW_SERVICE_KEY")
        # Lazy init client only if credentials available
        
    def extract(self, uploaded_file) -> dict[str, Any]:
        """Returns {'service': name, 'error'?: msg, ...extraction data}"""
        start_time = time.time()
        try:
            # Process file
            result = {
                "service": self.service_name,
                "file_name": uploaded_file.name,
                "processing_time": time.time() - start_time,
                # ... extraction data
            }
            return result
        except Exception as e:
            return {"service": self.service_name, "error": str(e)}
```

## 2. Add Environment Variables
Update `.env` template in README and add comments in code:
```env
# New Service
AZURE_NEW_SERVICE_ENDPOINT=https://...
AZURE_NEW_SERVICE_KEY=...
```

## 3. Import Handler
Add import in `handlers/__init__.py`:
```python
from .new_service import NewService
```

Import in `app.py`:
```python
from handlers import NewService
```

## 4. Add UI Checkbox
In `app.py`, add service selection checkbox:
```python
st.checkbox("New Service", key="new_service")
```

## 5. Create Test Fixtures (if needed)
Add mock fixtures in `tests/conftest.py` for testing.

## 6. Add Unit Tests
Add handler tests to `tests/test_handlers.py`:
```python
@pytest.mark.unit
def test_new_service_extract(mock_pdf_file):
    handler = NewService()
    result = handler.extract(mock_pdf_file)
    assert "service" in result
```

## Checklist
- [ ] Handler implements `__init__()` and `extract()`
- [ ] Environment variables documented
- [ ] Handler imported in `__init__.py` and `app.py`
- [ ] UI checkbox added
- [ ] Unit tests written with `@pytest.mark.unit`
- [ ] Tests pass: `make test-unit`
- [ ] Code formatted: `make format`
- [ ] Follows handler contract pattern
