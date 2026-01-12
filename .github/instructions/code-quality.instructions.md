---
description: Code quality standards and Ruff configuration
applyTo: '**/*.py'
---

# Code Quality Standards (Ruff)

## Formatting Rules

- **Line length**: 100 chars (enforced in `pyproject.toml`)
- **Quotes**: Double quotes only
- **Target**: Python 3.11+
- **Pre-commit**: Run `make format` before every commit

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
