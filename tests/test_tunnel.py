import asyncio
from types import SimpleNamespace

from pymobiledevice3.exceptions import UserspaceTunnelUnavailableError

from init import tunnel


def test_linux_userspace_backend_selected_when_available(monkeypatch):
    events = []
    monkeypatch.setattr(tunnel.platform, "system", lambda: "Linux")

    class FakeUserspace:
        async def aopen(self):
            events.append("userspace-open")
            return SimpleNamespace(is_in_process_tunnel=True)

        async def aclose(self):
            events.append("userspace-close")

    monkeypatch.setattr(tunnel.connect, "create_userspace_tunnel", lambda serial: FakeUserspace())

    async def exercise():
        handle = tunnel.create("userspace-device")
        async with handle as rsd:
            assert handle.backend == "userspace/CoreDeviceProxy"
            assert rsd.is_in_process_tunnel is True

    asyncio.run(exercise())
    assert events == ["userspace-open", "userspace-close"]


def test_linux_tunneld_fallback_on_userspace_unavailable(monkeypatch):
    events = []
    monkeypatch.setattr(tunnel.platform, "system", lambda: "Linux")

    class FakeUserspace:
        async def aopen(self):
            events.append("userspace-open")
            raise UserspaceTunnelUnavailableError()

        async def aclose(self):
            events.append("userspace-close")

    class FakeRsd:
        async def close(self):
            events.append("tunneld-close")

    monkeypatch.setattr(tunnel.connect, "create_userspace_tunnel", lambda serial: FakeUserspace())
    async def fake_get_tunneld_device_by_udid(udid):
        assert udid == "old-device"
        return FakeRsd()

    monkeypatch.setattr(tunnel, "get_tunneld_device_by_udid", fake_get_tunneld_device_by_udid)

    async def exercise():
        handle = tunnel.create("old-device")
        async with handle as rsd:
            assert handle.backend == "tunneld"
            assert isinstance(rsd, FakeRsd)

    asyncio.run(exercise())
    assert events == ["userspace-open", "userspace-close", "tunneld-close"]


def test_windows_tunneld_fallback_on_userspace_unavailable(monkeypatch):
    events = []
    monkeypatch.setattr(tunnel.platform, "system", lambda: "Windows")

    class FakeUserspace:
        async def aopen(self):
            events.append("userspace-open")
            raise UserspaceTunnelUnavailableError()

        async def aclose(self):
            events.append("userspace-close")

    class FakeRsd:
        async def close(self):
            events.append("tunneld-close")

    monkeypatch.setattr(tunnel.connect, "create_userspace_tunnel", lambda serial: FakeUserspace())

    async def fake_get_tunneld_device_by_udid(udid):
        assert udid == "windows-device"
        events.append("tunneld-open")
        return FakeRsd()

    monkeypatch.setattr(tunnel, "get_tunneld_device_by_udid", fake_get_tunneld_device_by_udid)

    async def exercise():
        handle = tunnel.create("windows-device")
        async with handle as rsd:
            assert handle.backend == "tunneld"
            assert isinstance(rsd, FakeRsd)

    asyncio.run(exercise())
    assert events == ["userspace-open", "userspace-close", "tunneld-open", "tunneld-close"]


def test_macos_native_remoted_fallback_on_userspace_unavailable(monkeypatch):
    events = []
    monkeypatch.setattr(tunnel.platform, "system", lambda: "Darwin")

    class FakeUserspace:
        async def aopen(self):
            events.append("userspace-open")
            raise UserspaceTunnelUnavailableError()

        async def aclose(self):
            events.append("userspace-close")

    class FakeNative:
        def __init__(self, serial):
            assert serial == "mac-device"

        async def aopen(self):
            events.append("native-open")
            return SimpleNamespace(is_native=True)

        async def aclose(self):
            events.append("native-close")

    async def unexpected_tunneld(_udid):
        raise AssertionError("macOS must not require tunneld after userspace is unavailable")

    monkeypatch.setattr(tunnel.connect, "create_userspace_tunnel", lambda serial: FakeUserspace())
    monkeypatch.setattr(tunnel, "NativeRemotedTunnel", FakeNative)
    monkeypatch.setattr(tunnel, "get_tunneld_device_by_udid", unexpected_tunneld)

    async def exercise():
        handle = tunnel.create("mac-device")
        async with handle as rsd:
            assert handle.backend == "native/remoted"
            assert rsd.is_native is True

    asyncio.run(exercise())
    assert events == ["userspace-open", "userspace-close", "native-open", "native-close"]


def test_unrelated_userspace_exception_propagates_without_fallback(monkeypatch):
    events = []
    monkeypatch.setattr(tunnel.platform, "system", lambda: "Linux")

    class FakeUserspace:
        async def aopen(self):
            events.append("userspace-open")
            raise RuntimeError("unexpected tunnel failure")

        async def aclose(self):
            events.append("userspace-close")

    async def unexpected_tunneld(_udid):
        raise AssertionError("unexpected userspace errors must not trigger fallback")

    monkeypatch.setattr(tunnel.connect, "create_userspace_tunnel", lambda serial: FakeUserspace())
    monkeypatch.setattr(tunnel, "get_tunneld_device_by_udid", unexpected_tunneld)

    async def exercise():
        handle = tunnel.create("broken-device")
        try:
            await handle.__aenter__()
        except RuntimeError as error:
            assert str(error) == "unexpected tunnel failure"
        else:
            raise AssertionError("the userspace error should propagate")

    asyncio.run(exercise())
    assert events == ["userspace-open", "userspace-close"]
