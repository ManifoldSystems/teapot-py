# teapot-py

Python client for Teapot (ManifoldSystems devprod tooling). Owner: Eric.
Thin layer over httpx: `proxy_url()` puts the exit name in the proxy
username; `Teapot.exits()` reads `GET /_teapot/exits` from the local agent;
`via="*"` rotates over online exits with distinct public IPv4
(`rotation_order`). Sync `Teapot`, async `AsyncTeapot`.

The behaviour it relies on lives in the agent: `ManifoldSystems/teapot`
(`crates/teapot-core/src/proxy.rs`, spec in `docs/protocol.md` under "Local
HTTP proxy"). Change the spec there first.

```bash
uv sync && uv run pytest && uv run ruff check . && uv run ruff format .
```

Live tests (`-m live`) need an agent on 127.0.0.1:1080 and spend real
traffic through exits (one exit is a phone on mobile data — keep them small).
`trust_env=False` everywhere: a system HTTP(S)_PROXY must not wrap the agent.
