import logging
import multiprocessing

from pymobiledevice3.lockdown import create_using_usbmux, LockdownClient
from pymobiledevice3.remote.tunnel_service import CoreDeviceTunnelProxy
from pymobiledevice3.services.amfi import AmfiService
from pymobiledevice3.exceptions import NoDeviceConnectedError

logger = logging.getLogger(__name__)


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


async def create_tunnel_from_lockdown(queue: multiprocessing.Queue):
    lockdown = await get_usbmux_lockdownclient()
    proxy = await CoreDeviceTunnelProxy.create(lockdown)
    logger.info("CoreDeviceTunnelProxy created, starting TCP tunnel")
    async with proxy.start_tcp_tunnel() as tunnel_result:
        queue.put({
            "status": "ok",
            "address": tunnel_result.address,
            "port": tunnel_result.port,
            "protocol": "TCP",
        })
        logger.info("tunnel established, address=%s port=%s", tunnel_result.address, tunnel_result.port)
        await tunnel_result.client.wait_closed()
