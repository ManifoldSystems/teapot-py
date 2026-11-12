# teapot-py

Send HTTP requests out of a chosen [Teapot](https://github.com/ManifoldSystems/teapot)
exit node: pick **where the request leaves the internet** per call, or rotate
over every exit with a different public IP. Built on [httpx](https://www.python-httpx.org/).

Needs the Teapot agent running on the same machine (`teapot service install`),
which serves an HTTP proxy on `127.0.0.1:1080`.

```bash
uv add "teapot-py @ git+https://github.com/ManifoldSystems/teapot-py"
# or: pip install "git+https://github.com/ManifoldSystems/teapot-py"
```

## Use

```python
from teapot import Teapot

tp = Teapot()

for e in tp.exits(online_only=True):  # what you can route through
    print(e.name, e.public_ipv4, "(default)" if e.default else "")

# Where to, with what payload, and out of which exit
r = tp.post(
    "https://api.example.com/v1/orders",
    json={"sku": "A-1", "qty": 2},
    headers={"Authorization": "Bearer …"},
    via="phone-exit",  # leave through the phone's SIM
)

tp.ip(via="home-exit")  # e.g. '198.51.100.20' (example IP)
tp.get("https://example.com")  # agent's default exit

# IP rotation: next exit with a different public IP each call
for _ in range(3):
    print(tp.ip(via="*"))

# Many requests through one exit
with tp.client(via="phone-exit") as c:
    c.get("https://example.com/a")
    c.get("https://example.com/b")
```

Async:

```python
from teapot import AsyncTeapot

tp = AsyncTeapot()
r = await tp.get("https://example.com", via="cloud-exit")
async with tp.client(via="*") as c:
    ...
```

`via` takes an exit name, its endpoint id, an id prefix (≥ 8 chars), `"*"` to
rotate, or `None` for the agent's default. A named exit that is offline or not
enabled raises `TeapotError` — there is no silent fallback.

HTTPS stays end to end between your code and the target; the exit node only
sees the host name and encrypted bytes. If both the exit and the target speak
IPv6, the target may see the exit's IPv6 address.

## How it works

The proxy username names the exit: `http://<exit>@127.0.0.1:1080`. Clients
send it as `Proxy-Authorization`, on `CONNECT` too, and the agent opens that
request's stream on a connection to the named exit. `GET /_teapot/exits` on the
proxy lists the exits. Any HTTP client can do the same without this library:

```bash
curl -x http://home-exit@127.0.0.1:1080 https://ifconfig.me
curl http://127.0.0.1:1080/_teapot/exits
```

## Develop

```bash
uv sync
uv run pytest -m 'not live'  # offline tests
uv run pytest -m live        # optional: uses a running agent and real exit traffic
uv run ruff check . && uv run ruff format .
```

## License

MIT — see [LICENSE](LICENSE).

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) for development checks and pull requests,
and [SECURITY.md](SECURITY.md) for vulnerability reporting.
