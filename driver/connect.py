import multiprocessing

from pymobiledevice3.lockdown import create_using_usbmux, LockdownClient

from pymobiledevice3.remote.common import TunnelProtocol
from pymobiledevice3.remote.module_imports import start_tunnel, verify_tunnel_imports
from pymobiledevice3.remote.tunnel_service import get_core_device_tunnel_services

from pymobiledevice3.services.amfi import AmfiService

from pymobiledevice3.exceptions import NoDeviceConnectedError

async def get_usbmux_lockdownclient():
    while True:
        try:
            lockdown = await create_using_usbmux()
        except NoDeviceConnectedError:
            print("请连接设备后按回车...")
            input()
        else:
            break
    while True:
        lockdown = await create_using_usbmux()
        if lockdown.all_values.get("PasswordProtected"):
            print("请解锁设备后按回车...")
            input()
        else:
            break
    return await create_using_usbmux()

def get_version(lockdown: LockdownClient):
    return lockdown.all_values.get("ProductVersion")

async def get_developer_mode_status(lockdown: LockdownClient):
    return await lockdown.get_developer_mode_status()

async def reveal_developer_mode(lockdown: LockdownClient):
    await AmfiService(lockdown).reveal_developer_mode_option_in_ui()

async def enable_developer_mode(lockdown: LockdownClient):
    await AmfiService(lockdown).enable_developer_mode()


async def tunnel(queue: multiprocessing.Queue):
    if not verify_tunnel_imports():
        exit(1)

    services = await get_core_device_tunnel_services()
    if not services:
        raise NoDeviceConnectedError()
    service = services[0]

    try:
        # iOS 18.2+ removed QUIC tunnel support, so TCP must be used. On
        # Python < 3.13 this relies on the sslpsk_pmd3 PSK-TLS fallback.
        async with start_tunnel(service, protocol=TunnelProtocol.TCP) as tunnel_result:
            queue.put((tunnel_result.address, tunnel_result.port))
            await tunnel_result.client.wait_closed()
    finally:
        await service.close()
