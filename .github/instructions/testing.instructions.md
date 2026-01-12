---
description: Testing strategy, patterns, and fixtures
applyTo: 'tests/*.py'
---

# Testing Strategy

## Test Types

### Unit Tests
- **Command**: `make test-unit`
- **Speed**: Fast, isolated
- **Marker**: `@pytest.mark.unit`
- **Characteristics**: No Azure API calls; uses mocks

### Integration Tests
- **Command**: `uv run pytest -m integration`
- **Requirements**: Requires `.env` credentials
- **Characteristics**: Tests real Azure service connections

### Coverage
- **Command**: `make test-cov`
- **Output**: HTML report in `htmlcov/index.html`
- **Target**: 100% coverage maintained

## Available Fixtures

Defined in `tests/conftest.py`:

- `sample_image_file`: Valid image file for testing
- `mock_pdf_file`: Mocked PDF file
- `mock_invalid_file`: Invalid file type for error testing
- `mock_empty_file`: Empty file for edge case testing

## Running Tests

```bash
make test-unit              # Run unit tests only (fast)
uv run pytest               # Run all tests with project environment
uv run pytest -m integration  # Run integration tests only
make test-cov               # Generate coverage report
```

## Test Writing Guidelines

1. **Mark tests appropriately**: Use `@pytest.mark.unit` or `@pytest.mark.integration`
2. **Mock Azure services**: For unit tests, mock all external API calls
3. **Use fixtures**: Reuse conftest fixtures rather than creating test data inline
4. **Test error paths**: Always test both success and error scenarios
5. **Verify handler contract**: Ensure handlers return expected dict structure

## Example Test Pattern

```python
@pytest.mark.unit
def test_handler_extract_success(mock_pdf_file):
    """Test successful extraction with valid input."""
    handler = ServiceHandler()
    result = handler.extract(mock_pdf_file)
    
    assert "service" in result
    assert "error" not in result
    assert "processing_time" in result
```
