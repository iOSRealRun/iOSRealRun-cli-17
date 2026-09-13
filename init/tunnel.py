"""Capability-driven RSD tunnel selection for iOS 17+ developer services."""

import logging
import platform

from pymobiledevice3.exceptions import UserspaceTunnelUnavailableError
from pymobiledevice3.remote.native_tunnel import NativeRemotedTunnel
from pymobiledevice3.remote.remote_service_discovery import (
    RemoteServiceDiscoveryService,
)
from pymobiledevice3.tunneld.api import get_tunneld_device_by_udid

from driver import connect

logger = logging.getLogger(__name__)


class AdaptiveRsdTunnel:
    """Use the platform-appropriate RSD tunnel when userspace is unavailable.

    The userspace attempt is the capability probe. pymobiledevice3 raises
    ``UserspaceTunnelUnavailableError`` when the device does not expose the
    CoreDeviceProxy path, which is the supported signal for older iOS 17.
    Linux and Windows use a running tunneld in that case; macOS uses
    pymobiledevice3's native remoted tunnel.
    """

    def __init__(self, serial: str):
        self.serial = serial
        self.backend: str | None = None
        self.rsd: RemoteServiceDiscoveryService | None = None
        self._userspace = None
        self._native = None

    async def __aenter__(self) -> RemoteServiceDiscoveryService:
        self._userspace = connect.create_userspace_tunnel(serial=self.serial)
        try:
            self.rsd = await self._userspace.aopen()
        except UserspaceTunnelUnavailableError:
            host = platform.system()
            await self._userspace.aclose()
            self._userspace = None
            if host == "Darwin":
                logger.info(
                    "CoreDevice userspace tunnel is unavailable; using native macOS/remoted tunnel"
                )
                self._native = NativeRemotedTunnel(serial=self.serial)
                self.rsd = await self._native.aopen()
                self.backend = "native/remoted"
                logger.info("selected native/remoted backend for device %s", self.serial)
            else:
                logger.info(
                    "CoreDevice userspace tunnel is unavailable; falling back to privileged tunneld"
                )
                self.rsd = await get_tunneld_device_by_udid(self.serial)
                if self.rsd is None:
                    command = (
                        "sudo .venv/bin/python -m pymobiledevice3 remote tunneld"
                        if host == "Linux"
                        else "run an elevated terminal: python -m pymobiledevice3 remote tunneld"
                    )
                    raise RuntimeError(
                        "pymobiledevice3 could not find this device in tunneld. "
                        "For iOS 17.0-17.3.1, start `"
                        f"{command}` in another terminal."
                    )
                self.backend = "tunneld"
                logger.info("selected tunneld backend for device %s", self.serial)
        except BaseException:
            # aopen() normally unwinds its own partial setup, but closing the
            # handle here also covers failures outside that internal lifecycle.
            await self._userspace.aclose()
            self._userspace = None
            raise
        else:
            self.backend = "userspace/CoreDeviceProxy"
            logger.info("selected userspace/CoreDeviceProxy backend for device %s", self.serial)
        return self.rsd

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._userspace is not None:
            await self._userspace.aclose()
        elif self._native is not None:
            await self._native.aclose()
        elif self.rsd is not None:
            await self.rsd.close()
        self.rsd = None
        self._native = None
        self.backend = None


def create(serial: str) -> AdaptiveRsdTunnel:
    """Return a capability-driven, closeable RSD connection handle."""
    return AdaptiveRsdTunnel(serial=serial)
