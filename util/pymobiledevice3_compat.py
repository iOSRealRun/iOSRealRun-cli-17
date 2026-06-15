import asyncio
import inspect
import logging
import os
from contextlib import AsyncExitStack, contextmanager, suppress
from importlib import import_module

from pymobiledevice3.exceptions import NoDeviceConnectedError
from pymobiledevice3.lockdown import create_using_usbmux


def _import_attr(module_name: str, attr_name: str):
    module = import_module(module_name)
    return getattr(module, attr_name)


def _import_first(*candidates):
    last_error = None
    for module_name, attr_name in candidates:
        try:
            return _import_attr(module_name, attr_name)
        except (ImportError, AttributeError) as error:
            last_error = error
    if last_error is not None:
        raise last_error
    raise ImportError("No import candidates were provided")


RemoteServiceDiscoveryService = _import_first(
    ("pymobiledevice3.remote.remote_service_discovery", "RemoteServiceDiscoveryService"),
    ("pymobiledevice3.cli.remote", "RemoteServiceDiscoveryService"),
)

LocationSimulation = _import_first(
    ("pymobiledevice3.services.dvt.instruments.location_simulation", "LocationSimulation"),
    ("pymobiledevice3.cli.developer", "LocationSimulation"),
)

_start_tunnel = _import_first(
    ("pymobiledevice3.remote.module_imports", "start_tunnel"),
    ("pymobiledevice3.cli.remote", "start_tunnel"),
)

try:
    _verify_tunnel_imports = _import_first(
        ("pymobiledevice3.remote.module_imports", "verify_tunnel_imports"),
        ("pymobiledevice3.cli.remote", "verify_tunnel_imports"),
    )
except (ImportError, AttributeError):
    _verify_tunnel_imports = None

try:
    _install_driver_if_required = _import_first(
        ("pymobiledevice3.cli.remote", "install_driver_if_required"),
    )
except (ImportError, AttributeError):
    _install_driver_if_required = None

try:
    _select_device = _import_first(
        ("pymobiledevice3.cli.remote", "select_device"),
    )
except (ImportError, AttributeError):
    _select_device = None

try:
    _prompt_device_list = _import_first(
        ("pymobiledevice3.cli.cli_common", "prompt_device_list"),
    )
except (ImportError, AttributeError):
    _prompt_device_list = None

try:
    _get_core_device_tunnel_services = _import_first(
        ("pymobiledevice3.remote.tunnel_service", "get_core_device_tunnel_services"),
    )
except (ImportError, AttributeError):
    _get_core_device_tunnel_services = None

try:
    CoreDeviceTunnelProxy = _import_first(
        ("pymobiledevice3.remote.tunnel_service", "CoreDeviceTunnelProxy"),
    )
except (ImportError, AttributeError):
    CoreDeviceTunnelProxy = None

try:
    TunnelProtocol = _import_first(
        ("pymobiledevice3.remote.common", "TunnelProtocol"),
    )
except (ImportError, AttributeError):
    TunnelProtocol = None

try:
    DvtProvider = _import_first(
        ("pymobiledevice3.services.dvt.instruments.dvt_provider", "DvtProvider"),
    )
except (ImportError, AttributeError):
    DvtProvider = None

try:
    DvtSecureSocketProxyService = _import_first(
        ("pymobiledevice3.cli.developer", "DvtSecureSocketProxyService"),
    )
except (ImportError, AttributeError):
    DvtSecureSocketProxyService = None

try:
    DtSimulateLocation = _import_first(
        ("pymobiledevice3.services.simulate_location", "DtSimulateLocation"),
    )
except (ImportError, AttributeError):
    DtSimulateLocation = None

try:
    ConnectionTerminatedError = _import_first(
        ("pymobiledevice3.exceptions", "ConnectionTerminatedError"),
    )
except (ImportError, AttributeError):
    ConnectionTerminatedError = None

_TRANSIENT_LOCATION_ERRORS = tuple(
    error
    for error in (
        ConnectionTerminatedError,
        ConnectionResetError,
        BrokenPipeError,
        OSError,
    )
    if error is not None
)

_LOCATION_RETRIES = int(os.environ.get("LOCATION_RETRIES", "5"))
_DVT_SESSION_CALLS = int(os.environ.get("DVT_SESSION_CALLS", "250"))
logger = logging.getLogger(__name__)


class UsbTunnelService:
    pass


def install_driver_if_required():
    if _install_driver_if_required is not None:
        _install_driver_if_required()


def verify_tunnel_imports() -> bool:
    if _verify_tunnel_imports is None:
        return True
    return bool(_verify_tunnel_imports())


def _preferred_protocol():
    if TunnelProtocol is None:
        return None
    return getattr(TunnelProtocol, "TCP", None)


def _wait_if_needed(result):
    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result


async def _await_if_needed(result):
    if inspect.isawaitable(result):
        return await result
    return result


async def _select_tunnel_service():
    if CoreDeviceTunnelProxy is not None:
        return UsbTunnelService()

    if _get_core_device_tunnel_services is None:
        if _select_device is not None:
            return _select_device(None)
        raise ImportError("No compatible tunnel discovery API was found")

    services = []
    for _ in range(5):
        services = await _get_core_device_tunnel_services()
        if services:
            break
        await asyncio.sleep(1)

    if not services:
        raise NoDeviceConnectedError()

    if len(services) == 1 or _prompt_device_list is None:
        return services[0]
    return _prompt_device_list(services)


def get_tunnel_service():
    return asyncio.run(_select_tunnel_service())


def _build_tunnel_kwargs():
    kwargs = {}
    parameters = inspect.signature(_start_tunnel).parameters
    if "secrets" in parameters:
        kwargs["secrets"] = None
    protocol = _preferred_protocol()
    if protocol is not None and "protocol" in parameters:
        kwargs["protocol"] = protocol
    return kwargs


async def start_tunnel(service, queue):
    if isinstance(service, UsbTunnelService):
        lockdown = await _await_if_needed(create_using_usbmux())
        service = await CoreDeviceTunnelProxy.create(lockdown)

    async with _start_tunnel(service, **_build_tunnel_kwargs()) as tunnel_result:
        queue.put((tunnel_result.address, tunnel_result.port))
        await tunnel_result.client.wait_closed()


class _LocationClient:
    def __init__(self, service, loop=None):
        self._service = service
        self._loop = loop

    def set(self, latitude: float, longitude: float):
        result = self._service.set(latitude, longitude)
        if inspect.isawaitable(result) and self._loop is not None:
            return self._loop.run_until_complete(result)
        return _wait_if_needed(result)

    def clear(self):
        result = self._service.clear()
        if inspect.isawaitable(result) and self._loop is not None:
            return self._loop.run_until_complete(result)
        return _wait_if_needed(result)


class _DvtLocationClient:
    def __init__(self, service_provider, loop):
        self._service_provider = service_provider
        self._loop = loop
        self._exit_stack = None
        self._location = None
        self._calls_since_open = 0

    async def _open(self):
        self._exit_stack = AsyncExitStack()
        dvt = await self._exit_stack.enter_async_context(DvtProvider(self._service_provider))
        self._location = await self._exit_stack.enter_async_context(LocationSimulation(dvt))
        self._calls_since_open = 0

    def open(self):
        self._loop.run_until_complete(self._open())

    async def _reopen(self):
        await self._close()
        await self._open()

    async def _close(self):
        if self._exit_stack is not None:
            with suppress(Exception):
                await self._exit_stack.aclose()
        self._exit_stack = None
        self._location = None

    async def _refresh_if_needed(self):
        if self._calls_since_open >= _DVT_SESSION_CALLS:
            logger.info("Refreshing DVT location session after %s updates", self._calls_since_open)
            await self._reopen()

    async def _run_with_reconnect(self, operation):
        last_error = None
        for attempt in range(1, _LOCATION_RETRIES + 1):
            try:
                await self._refresh_if_needed()
                result = await operation()
                self._calls_since_open += 1
                return result
            except Exception as error:
                last_error = error
                logger.warning(
                    "Location channel failed, reconnecting (%s/%s): %r",
                    attempt,
                    _LOCATION_RETRIES,
                    error,
                )
                await asyncio.sleep(min(0.2 * attempt, 1.0))
                await self._reopen()
        raise last_error

    def set(self, latitude: float, longitude: float):
        async def set_location():
            await self._location.set(latitude, longitude)

        self._loop.run_until_complete(self._run_with_reconnect(set_location))

    def clear(self):
        async def clear_location():
            await self._location.clear()

        self._loop.run_until_complete(self._run_with_reconnect(clear_location))

    def close(self):
        self._loop.run_until_complete(self._close())

    def refresh_session(self):
        self._loop.run_until_complete(self._reopen())


class _LegacyLocationClient:
    def __init__(self, dvt):
        self._dvt = dvt

    def set(self, latitude: float, longitude: float):
        return _wait_if_needed(LocationSimulation(self._dvt).set(latitude, longitude))

    def clear(self):
        return _wait_if_needed(LocationSimulation(self._dvt).clear())


@contextmanager
def open_remote_service_discovery(address, port):
    rsd = RemoteServiceDiscoveryService((address, port))
    if hasattr(rsd, "__enter__"):
        with rsd as connected_rsd:
            yield connected_rsd
        return

    loop = asyncio.new_event_loop()
    rsd._compat_loop = loop
    try:
        loop.run_until_complete(rsd.connect())
        yield rsd
    finally:
        loop.run_until_complete(rsd.close())
        loop.close()


@contextmanager
def open_location_session(service_provider):
    loop = getattr(service_provider, "_compat_loop", None)
    if DvtProvider is not None and loop is not None:
        client = _DvtLocationClient(service_provider, loop)
        client.open()
        try:
            yield client
        finally:
            client.close()
        return

    if DtSimulateLocation is not None:
        yield _LocationClient(DtSimulateLocation(service_provider), loop=loop)
        return

    if DvtSecureSocketProxyService is None:
        raise ImportError("No compatible location simulation API was found")

    with DvtSecureSocketProxyService(service_provider) as dvt:
        yield _LegacyLocationClient(dvt)
