"""Send HTTP requests out of a chosen Teapot exit node.

The local Teapot agent is an HTTP proxy (default ``127.0.0.1:1080``). The proxy
username names the exit for that request (``http://<exit>@127.0.0.1:1080``),
and ``GET /_teapot/exits`` on the proxy lists what can be named. This module is
a thin layer over httpx that builds those proxy URLs and adds rotation.
"""

from __future__ import annotations

import itertools
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import httpx

DEFAULT_PROXY = "http://127.0.0.1:1080"

#: ``via=ROTATE`` picks the next exit in round-robin over distinct public IPs.
ROTATE = "*"


class TeapotError(Exception):
    """The agent is unreachable or the requested exit cannot be used."""


@dataclass(frozen=True)
class Exit:
    name: str
    node_id: str
    online: bool
    public_ipv4: str | None
    default: bool

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Exit:
        return cls(
            name=data["name"],
            node_id=data["node_id"],
            online=bool(data.get("online")),
            public_ipv4=data.get("public_ipv4"),
            default=bool(data.get("default")),
        )


def proxy_url(proxy: str, via: str | None) -> str:
    """The proxy URL that routes through ``via`` (or the agent's default)."""
    if not via:
        return proxy
    parts = urlsplit(proxy)
    host = parts.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parts.scheme, f"{quote(via, safe='')}@{host}", parts.path, "", ""))


def rotation_order(exits: list[Exit]) -> list[str]:
    """Online exits, one per distinct public IPv4, default first.

    Several exits on the same network leave with the same IP; rotating over
    them would not change what the target sees.
    """
    seen: set[str] = set()
    order: list[str] = []
    for e in sorted(exits, key=lambda e: not e.default):
        if not e.online:
            continue
        key = e.public_ipv4 or e.node_id
        if key in seen:
            continue
        seen.add(key)
        order.append(e.name)
    return order


class _Rotation:
    """Thread-safe round robin, refreshed from the agent when it runs out."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cycle: Iterator[str] | None = None
        self._size = 0

    def next(self, load: Any) -> str:
        with self._lock:
            if self._cycle is None:
                order = rotation_order(load())
                if not order:
                    raise TeapotError("no online exit node to rotate over")
                self._cycle, self._size = itertools.cycle(order), len(order)
            return next(self._cycle)

    def reset(self) -> None:
        with self._lock:
            self._cycle = None


class Teapot:
    """Synchronous client.

    >>> tp = Teapot()
    >>> tp.get("https://ifconfig.me", via="phone-exit").text
    """

    def __init__(self, proxy: str = DEFAULT_PROXY, *, timeout: float = 30.0, **client_kwargs: Any) -> None:
        self.proxy = proxy.rstrip("/")
        self.timeout = timeout
        self._client_kwargs = client_kwargs
        self._rotation = _Rotation()

    # -- exits ---------------------------------------------------------------

    def exits(self, *, online_only: bool = False) -> list[Exit]:
        """Exits the agent can route through, from ``GET /_teapot/exits``."""
        try:
            res = httpx.get(f"{self.proxy}/_teapot/exits", timeout=self.timeout, trust_env=False)
            res.raise_for_status()
        except httpx.HTTPError as e:
            raise TeapotError(f"teapot agent not reachable at {self.proxy}: {e}") from e
        exits = [Exit.from_json(x) for x in res.json()["exits"]]
        return [e for e in exits if e.online] if online_only else exits

    def rotate(self) -> str:
        """Next exit name in the rotation (one per distinct public IP)."""
        return self._rotation.next(self.exits)

    # -- requests ------------------------------------------------------------

    def client(self, via: str | None = None, **kwargs: Any) -> httpx.Client:
        """An httpx.Client whose every request leaves through ``via``."""
        if via == ROTATE:
            via = self.rotate()
        opts = {"timeout": self.timeout, **self._client_kwargs, **kwargs}
        return httpx.Client(proxy=proxy_url(self.proxy, via), trust_env=False, **opts)

    def request(self, method: str, url: str, *, via: str | None = None, **kwargs: Any) -> httpx.Response:
        """One request through ``via`` (name, id prefix, ``"*"`` to rotate, or None)."""
        if via == ROTATE:
            via = self.rotate()
        with self.client(via) as c:
            try:
                return c.request(method, url, **kwargs)
            except httpx.ProxyError as e:
                raise TeapotError(_explain(via, e)) from e

    def get(self, url: str, **kw: Any) -> httpx.Response:
        return self.request("GET", url, **kw)

    def post(self, url: str, **kw: Any) -> httpx.Response:
        return self.request("POST", url, **kw)

    def put(self, url: str, **kw: Any) -> httpx.Response:
        return self.request("PUT", url, **kw)

    def patch(self, url: str, **kw: Any) -> httpx.Response:
        return self.request("PATCH", url, **kw)

    def delete(self, url: str, **kw: Any) -> httpx.Response:
        return self.request("DELETE", url, **kw)

    def ip(self, via: str | None = None) -> str:
        """Public IP a target sees for requests through ``via``."""
        return self.get("https://ifconfig.me/ip", via=via).text.strip()


class AsyncTeapot(Teapot):
    """Asynchronous client with the same options.

    >>> async with AsyncTeapot().client(via="home-exit") as c:
    ...     await c.get("https://example.com")
    """

    def client(self, via: str | None = None, **kwargs: Any) -> httpx.AsyncClient:  # type: ignore[override]
        if via == ROTATE:
            via = self.rotate()
        opts = {"timeout": self.timeout, **self._client_kwargs, **kwargs}
        return httpx.AsyncClient(proxy=proxy_url(self.proxy, via), trust_env=False, **opts)

    async def request(
        self, method: str, url: str, *, via: str | None = None, **kwargs: Any
    ) -> httpx.Response:  # type: ignore[override]
        if via == ROTATE:
            via = self.rotate()
        async with self.client(via) as c:
            try:
                return await c.request(method, url, **kwargs)
            except httpx.ProxyError as e:
                raise TeapotError(_explain(via, e)) from e

    async def get(self, url: str, **kw: Any) -> httpx.Response:  # type: ignore[override]
        return await self.request("GET", url, **kw)

    async def post(self, url: str, **kw: Any) -> httpx.Response:  # type: ignore[override]
        return await self.request("POST", url, **kw)

    async def put(self, url: str, **kw: Any) -> httpx.Response:  # type: ignore[override]
        return await self.request("PUT", url, **kw)

    async def patch(self, url: str, **kw: Any) -> httpx.Response:  # type: ignore[override]
        return await self.request("PATCH", url, **kw)

    async def delete(self, url: str, **kw: Any) -> httpx.Response:  # type: ignore[override]
        return await self.request("DELETE", url, **kw)

    async def ip(self, via: str | None = None) -> str:  # type: ignore[override]
        return (await self.get("https://ifconfig.me/ip", via=via)).text.strip()


def _explain(via: str | None, err: Exception) -> str:
    where = f"exit {via!r}" if via else "the default exit"
    return f"could not route through {where}: {err}. See `curl {DEFAULT_PROXY}/_teapot/exits`."
