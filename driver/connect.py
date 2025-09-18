import logging
import multiprocessing

from pymobiledevice3.lockdown import create_using_usbmux, LockdownClient

# select_device and install_driver_if_required were
# already deprecated in pymobiledevice3 v4.14.11
from pymobiledevice3.remote.utils import get_rsds
from pymobiledevice3.cli.remote import RemoteServiceDiscoveryService
from pymobiledevice3.remote.tunnel_service import (
    start_tunnel,
    create_core_device_tunnel_service_using_rsd,
    TunnelProtocol
)

from pymobiledevice3.services.amfi import AmfiService

from pymobiledevice3.exceptions import NoDeviceConnectedError

def get_usbmux_lockdownclient():
    while True:
        try:
            lockdown = create_using_usbmux()
        except NoDeviceConnectedError:
            print("请连接设备后按回车...")
            input()
        else:
            break
    while True:
        lockdown = create_using_usbmux()
        if lockdown.all_values.get("PasswordProtected"):
            print("请解锁设备后按回车...")
            input()
        else:
            break
    return create_using_usbmux()

def get_version(lockdown: LockdownClient):
    return lockdown.all_values.get("ProductVersion")

def get_developer_mode_status(lockdown: LockdownClient):
    return lockdown.developer_mode_status

def reveal_developer_mode(lockdown: LockdownClient):
    AmfiService(lockdown).create_amfi_show_override_path_file()

def enable_developer_mode(lockdown: LockdownClient):
    AmfiService(lockdown).enable_developer_mode()


async def get_serverrsd():
    # install_driver_if_required() not required in MacOS
    rsds = await get_rsds()
    if not rsds:
        raise NoDeviceConnectedError("未发现可用设备或 RSD 服务")
    rsd = rsds[0]
    return rsd


async def tunnel(rsd: RemoteServiceDiscoveryService, queue: multiprocessing.Queue):
    # 先构造协议处理器（CoreDeviceTunnelService）
    service = await create_core_device_tunnel_service_using_rsd(rsd)
    # ios18.7 测试，改用 TCP 协议才能成功
    async with start_tunnel(service, protocol=TunnelProtocol.TCP) as tunnel_result:
        queue.put((tunnel_result.address, tunnel_result.port))
        await tunnel_result.client.wait_closed()
