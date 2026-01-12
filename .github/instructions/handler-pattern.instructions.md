---
description: Handler implementation contract and patterns
applyTo: 'handlers/*.py'
---

# Handler Contract (Concrete Pattern)

All handlers in `handlers/` follow this structure (no BaseHandler base class; implementations are independent):

```python
class ServiceName:
    def __init__(self, service_name: str = None):
        self.service_name = service_name
        self.endpoint = os.environ.get("AZURE_SERVICE_ENDPOINT")
        self.key = os.environ.get("AZURE_SERVICE_KEY")
        # Lazy init client only if credentials available
        
    def extract(self, uploaded_file) -> dict[str, Any]:
        """Returns {'service': name, 'error'?: msg, ...extraction data}"""
        start_time = time.time()
        # Process file; catch exceptions as dicts with 'error' key
        processing_time = time.time() - start_time
        return {...}
```

## Key Requirements

1. **Return Type**: Always return `dict[str, Any]`
2. **Error Handling**: Catch exceptions and return `{'error': str}` instead of crashing
3. **Service Key**: Always include `'service'` key with service name
4. **Timing**: Track `processing_time` for performance metrics
5. **Lazy Init**: Only initialize Azure clients if credentials are available

## Reference Implementation

See `handlers/document_intelligence.py` for the canonical example.

## Session State Persistence (Streamlit)

When working with Streamlit components:

```python
from utils import keep_state
keep_state(valid_files, "valid_files")      # Persist across page changes
keep_state(selected_services, "selected_services")
```

## JSON Normalization

Use the utility function to save results:

```python
from utils import save_extraction_to_json
save_extraction_to_json(
    file_name="doc.pdf",
    service_name="GPT-4.1-Vision", 
    pages_count=1,
    fields={"field_name": {"content": "text", "confidence": 0.98}},
    processing_time=2.5
)  # Auto-deduplicates (file_name, service_name) pairs
```
