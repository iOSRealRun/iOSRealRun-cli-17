import asyncio
import inspect
import multiprocessing

from pymobiledevice3.lockdown import create_using_usbmux, LockdownClient

from pymobiledevice3.services.amfi import AmfiService

from pymobiledevice3.exceptions import NoDeviceConnectedError

from util.pymobiledevice3_compat import (
    RemoteServiceDiscoveryService,
    get_tunnel_service,
    install_driver_if_required,
    start_tunnel as start_tunnel_session,
    verify_tunnel_imports,
)


def _wait_if_needed(result):
    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result


def _create_using_usbmux():
    return _wait_if_needed(create_using_usbmux())


async def _create_using_usbmux_async():
    lockdown = create_using_usbmux()
    if inspect.isawaitable(lockdown):
        lockdown = await lockdown
    return lockdown


def get_usbmux_lockdownclient():
    while True:
        try:
            lockdown = _create_using_usbmux()
        except NoDeviceConnectedError:
            print("请连接设备后按回车...")
            input()
        else:
            break
    while True:
        lockdown = _create_using_usbmux()
        if lockdown.all_values.get("PasswordProtected"):
            print("请解锁设备后按回车...")
            input()
        else:
            break
    return lockdown

def get_version(lockdown: LockdownClient):
    return lockdown.all_values.get("ProductVersion")

def get_developer_mode_status(lockdown: LockdownClient):
    if hasattr(lockdown, "developer_mode_status"):
        return lockdown.developer_mode_status

    async def get_status():
        fresh_lockdown = await _create_using_usbmux_async()
        return await fresh_lockdown.get_developer_mode_status()

    return asyncio.run(get_status())

def reveal_developer_mode(lockdown: LockdownClient):
    service = AmfiService(lockdown)
    if hasattr(service, "create_amfi_show_override_path_file"):
        return _wait_if_needed(service.create_amfi_show_override_path_file())

    async def reveal():
        fresh_lockdown = await _create_using_usbmux_async()
        await AmfiService(fresh_lockdown).reveal_developer_mode_option_in_ui()

    return asyncio.run(reveal())

def enable_developer_mode(lockdown: LockdownClient):
    service = AmfiService(lockdown)
    if not inspect.iscoroutinefunction(service.enable_developer_mode):
        return service.enable_developer_mode()

    async def enable():
        fresh_lockdown = await _create_using_usbmux_async()
        await AmfiService(fresh_lockdown).enable_developer_mode()

    return asyncio.run(enable())

def get_serverrsd():
    install_driver_if_required()
    if not verify_tunnel_imports():
        exit(1)
    return get_tunnel_service()


async def tunnel(rsd: RemoteServiceDiscoveryService, queue: multiprocessing.Queue):
    await start_tunnel_session(rsd, queue)
