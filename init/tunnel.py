from contextlib import asynccontextmanager

from pymobiledevice3.remote.userspace_tunnel import UserspaceRsdTunnel


@asynccontextmanager
async def tunnel(serial=None):
    """建立 iOS 17+ 的进程内 userspace RSD 隧道。"""
    async with UserspaceRsdTunnel(serial=serial) as rsd:
        yield rsd
