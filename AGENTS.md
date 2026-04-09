# Project Context for Agents


## Tech Stack
- Language: Python 3.14
- Framework: Flask
- Test Runner: unittest
- Code quality: Qodana

## Rules
- Always use Type Hints
- Document functions with docstrings
- Use PEP8
- Do not write docstrings for modules unless asked.
- Do not modify the uv.lock and pyproject.toml files manually. They are managed by uv.
- When refactoring, always run `uv run python -m unittest discover src/test` before finishing.
- When making large numbers of HTTP requests (>10 per second), use aiohttp instead of requests for better performance. 
- Write docstrings in reStructuredText format.