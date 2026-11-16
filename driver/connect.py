import asyncio
import logging

from pymobiledevice3.exceptions import NoDeviceConnectedError
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.amfi import AmfiService

logger = logging.getLogger(__name__)


async def get_lockdown():
    """连接当前 USB 设备，等待用户连接、解锁并信任电脑。"""
    while True:
        try:
            return await create_using_usbmux()
        except NoDeviceConnectedError:
            print("未检测到 iPhone，请连接设备、解锁并点击“信任”，然后按回车重试...")
            await asyncio.to_thread(input)


def get_version(lockdown):
    return lockdown.all_values.get("ProductVersion")


async def get_developer_mode_status(lockdown):
    return await lockdown.get_developer_mode_status()


def reveal_developer_mode(lockdown):
    AmfiService(lockdown).create_amfi_show_override_path_file()


def enable_developer_mode(lockdown):
    AmfiService(lockdown).enable_developer_mode()
