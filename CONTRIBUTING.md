# Contributing

Install uv and Python 3.10 or newer:

```sh
uv sync --locked
uv run pytest -m 'not live'
uv run ruff check .
uv run ruff format --check .
uv build
```

CI tests Python 3.10 and 3.13. Live tests are opt-in (`uv run pytest -m live`):
they need an agent on localhost and send real traffic through your exit nodes.

Keep pull requests focused, describe behavior changes, and include verification.
Maintain parity between sync and async clients. Agent-side proxy behavior is
specified in `ManifoldSystems/teapot/docs/protocol.md`; coordinate changes there.
Use fictional exit names and documentation IPs in fixtures. Do not include
credentials or real fleet information in commits, issues, or logs.

Contributions use MIT; preserve notices required by reused code.
For vulnerabilities, see [SECURITY.md](SECURITY.md).
