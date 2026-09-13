"""Device discovery and modern pymobiledevice3 connection helpers."""

import asyncio
import logging

from pymobiledevice3.exceptions import NoDeviceConnectedError
from pymobiledevice3.lockdown import LockdownClient, create_using_usbmux
from pymobiledevice3.remote.userspace_tunnel import UserspaceRsdTunnel
from pymobiledevice3.services.amfi import AmfiService
from pymobiledevice3.usbmux import list_devices

logger = logging.getLogger(__name__)


async def discover_devices():
    """Return devices currently visible through the local usbmux daemon."""
    logger.debug("discovering devices through usbmux")
    devices = await list_devices()
    logger.info("usbmux discovered %d device(s)", len(devices))
    for device in devices:
        logger.debug("usbmux device: %s", device)
    return devices


async def get_usbmux_lockdownclient(serial: str | None = None) -> LockdownClient:
    """Connect to a paired USB device, waiting for the user when necessary."""
    while True:
        try:
            devices = await discover_devices()
            if not devices:
                raise NoDeviceConnectedError()

            logger.info("opening paired usbmux/lockdown connection")
            lockdown = await create_using_usbmux(serial=serial, autopair=True)
            logger.info("lockdown connection established for %s", lockdown.udid)
        except NoDeviceConnectedError:
            logger.warning("no iOS device available through usbmux")
            print("请连接设备后按回车...")
            await asyncio.to_thread(input)
            continue
        except Exception:
            logger.exception("usbmux/lockdown setup failed")
            raise

        if lockdown.all_values.get("PasswordProtected"):
            logger.warning("device is locked; unlock it before continuing")
            await lockdown.close()
            print("请解锁设备后按回车...")
            await asyncio.to_thread(input)
            continue
        return lockdown


def get_version(lockdown: LockdownClient) -> str:
    return lockdown.product_version


async def get_developer_mode_status(lockdown: LockdownClient) -> bool:
    status = await lockdown.get_developer_mode_status()
    logger.info("Developer Mode: %s", "enabled" if status else "disabled")
    return status


async def reveal_developer_mode(lockdown: LockdownClient) -> None:
    logger.info("requesting Developer Mode option reveal")
    await AmfiService(lockdown).reveal_developer_mode_option_in_ui()


def create_userspace_tunnel(serial: str | None = None) -> UserspaceRsdTunnel:
    """Create the CoreDevice userspace tunnel and let pymobiledevice3 detect capability."""
    logger.info("probing CoreDevice userspace tunnel capability (no root required)")
    # Disabling the pre-17.4 RemotePairing fallback is intentional on Linux. If this
    # capability probe fails, init/tunnel.py selects a running privileged tunneld instead.
    return UserspaceRsdTunnel(serial=serial, autopair=True, remotepairing_fallback=False)
