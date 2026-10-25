import socket

import pytest

from teapot import AsyncTeapot, Exit, Teapot, TeapotError, proxy_url, rotation_order


def ex(name, ip, online=True, default=False):
    return Exit(name=name, node_id=name * 8, online=online, public_ipv4=ip, default=default)


def test_proxy_url_names_the_exit():
    assert proxy_url("http://127.0.0.1:1080", None) == "http://127.0.0.1:1080"
    assert proxy_url("http://127.0.0.1:1080", "phone-exit") == "http://phone-exit@127.0.0.1:1080"
    assert proxy_url("http://old@127.0.0.1:1080", "home-exit") == "http://home-exit@127.0.0.1:1080"


def test_rotation_one_per_distinct_ip_default_first():
    exits = [
        ex("office-exit", "192.0.2.10"),
        ex("office-peer", "192.0.2.10"),  # same network as office-exit: skipped
        ex("phone-exit", "203.0.113.30", default=True),
        ex("home-exit", "198.51.100.20"),
        ex("offline-one", "1.2.3.4", online=False),
    ]
    assert rotation_order(exits) == ["phone-exit", "office-exit", "home-exit"]


def test_rotate_cycles(monkeypatch):
    tp = Teapot()
    monkeypatch.setattr(tp, "exits", lambda: [ex("a", "1.1.1.1"), ex("b", "2.2.2.2")])
    assert [tp.rotate() for _ in range(5)] == ["a", "b", "a", "b", "a"]


def test_unreachable_agent_is_a_teapot_error():
    with socket.socket() as s:  # a port nobody listens on
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    with pytest.raises(TeapotError, match="not reachable"):
        Teapot(f"http://127.0.0.1:{port}", timeout=2).exits()


def _agent_up() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 1080), timeout=1):
            return True
    except OSError:
        return False


live = pytest.mark.skipif(not _agent_up(), reason="no teapot agent on 127.0.0.1:1080")


@pytest.mark.live
@live
def test_live_each_exit_has_its_ip():
    tp = Teapot(timeout=60)
    exits = tp.exits(online_only=True)
    assert exits, "agent lists no online exits"
    target = next(e for e in exits if e.public_ipv4 and not e.default)
    seen = tp.ip(via=target.name)
    assert seen  # IPv6 is possible when target and exit both have it
    if ":" not in seen:
        assert seen == target.public_ipv4


@pytest.mark.live
@live
def test_live_unknown_exit_raises():
    with pytest.raises(TeapotError, match="no-such-exit"):
        Teapot(timeout=30).get("https://ifconfig.me", via="no-such-exit")


@pytest.mark.live
@live
async def test_live_async_rotation_changes_ip():
    tp = AsyncTeapot(timeout=60)
    ips = {await tp.ip(via="*") for _ in range(3)}
    assert len(ips) >= 2
