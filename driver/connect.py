import logging
import multiprocessing

from pymobiledevice3.lockdown import create_using_usbmux, LockdownClient

from pymobiledevice3.cli.remote import install_driver_if_required
from pymobiledevice3.cli.remote import select_device, RemoteServiceDiscoveryService
from pymobiledevice3.cli.remote import start_tunnel
from pymobiledevice3.cli.remote import verify_tunnel_imports

from pymobiledevice3.services.amfi import AmfiService

from pymobiledevice3.exceptions import NoDeviceConnectedError

# def get_usbmux_lockdownclient():
#     while True:
#         try:
#             lockdown = create_using_usbmux()
#         except NoDeviceConnectedError:
#             print("请连接设备后按回车...")
#             input()
#         else:
#             break
#     while True:
#         lockdown = create_using_usbmux()
#         if lockdown.all_values.get("PasswordProtected"):
#             print("请解锁设备后按回车...")
#             input()
#         else:
#             break
#     return create_using_usbmux()

# def get_version(lockdown: LockdownClient):
#     return lockdown.all_values.get("ProductVersion")

# def get_developer_mode_status(lockdown: LockdownClient):
#     return lockdown.developer_mode_status

# def reveal_developer_mode(lockdown: LockdownClient):
#     AmfiService(lockdown).create_amfi_show_override_path_file()

# def enable_developer_mode(lockdown: LockdownClient):
#     AmfiService(lockdown).enable_developer_mode()

def get_serverrsd():
    install_driver_if_required()
    if not verify_tunnel_imports():
        exit(1)
    return select_device(None)


async def tunnel(rsd: RemoteServiceDiscoveryService, queue: multiprocessing.Queue):
    async with start_tunnel(rsd, None) as tunnel_result:
        queue.put((tunnel_result.address, tunnel_result.port))
        await tunnel_result.client.wait_closed()
