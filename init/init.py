import logging
from dataclasses import dataclass

from driver import connect

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeviceInfo:
    udid: str
    version: str


async def init(serial=None):
    """Validate the device before opening the iOS 17+ developer tunnel."""
    logger.info("initializing device connection; tunnel backend will be selected by capability")

    lockdown = await connect.get_usbmux_lockdownclient(serial=serial)
    try:
        logger.debug("lockdown values received: %s", sorted(lockdown.all_values.keys()))

        version = connect.get_version(lockdown)
        print(f"Your system version is {version}")
        try:
            major_version = int(version.split(".", 1)[0])
        except (AttributeError, ValueError) as error:
            raise RuntimeError(f"could not parse iOS version: {version!r}") from error
        if major_version < 17:
            print("仅支持17及以上版本")
            raise SystemExit(1)

        developer_mode_status = await connect.get_developer_mode_status(lockdown)
        if not developer_mode_status:
            await connect.reveal_developer_mode(lockdown)
            print("您未开启开发者模式，请打开设备的 设置-隐私与安全性-开发者模式 来开启，开启后需要重启并输入密码，完成后再次运行此程序")
            raise SystemExit(1)
        return DeviceInfo(udid=lockdown.udid, version=version)
    finally:
        logger.debug("closing initialization lockdown connection")
        await lockdown.close()
