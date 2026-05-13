import signal
import logging
import coloredlogs
import os
import asyncio

from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

from init import init
from init import tunnel
from init import route

import run

import config


debug = os.environ.get("DEBUG", False)

coloredlogs.install(level=logging.INFO)
logging.getLogger('wintun').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('quic').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('zeroconf').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('parso.cache').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('parso.cache.pickle').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('parso.python.diff').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('humanfriendly.prompts').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('blib2to3.pgen2.driver').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.DEBUG if debug else logging.WARNING)

_cleanup_address = None
_cleanup_port = None
_cleanup_process = None


async def _do_clear_location():
    if _cleanup_address is None:
        return
    try:
        async with RemoteServiceDiscoveryService((_cleanup_address, _cleanup_port)) as rsd:
            async with DvtProvider(rsd) as dvt:
                async with LocationSimulation(dvt) as loc:
                    await asyncio.wait_for(loc.clear(), timeout=5.0)
                    print("定位已清除")
    except asyncio.TimeoutError:
        print("清除定位超时，请重启手机恢复")
    except Exception as e:
        print(f"清除定位时出错: {e}，请重启手机恢复")


async def _async_main():
    global _cleanup_address, _cleanup_port, _cleanup_process

    logger = logging.getLogger(__name__)
    coloredlogs.install(level=logging.INFO)
    logger.setLevel(logging.INFO)
    if debug:
        logger.setLevel(logging.DEBUG)
        coloredlogs.install(level=logging.DEBUG)

    await init.init()
    logger.info("init done")

    logger.info("starting tunnel")
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        _cleanup_process, _cleanup_address, _cleanup_port = tunnel.tunnel()
    except RuntimeError as exc:
        logger.error("failed to start tunnel: %s", exc)
        print(f"启动隧道失败：{exc}")
        return
    finally:
        signal.signal(signal.SIGINT, original_sigint_handler)
    logger.info("tunnel started")

    logger.debug(f"tunnel address: {_cleanup_address}, port: {_cleanup_port}")

    loc = route.get_route()
    logger.info(f"got route from {config.config.routeConfig}")

    async with RemoteServiceDiscoveryService((_cleanup_address, _cleanup_port)) as rsd:
        async with DvtProvider(rsd) as dvt:
            async with LocationSimulation(dvt) as loc_sim:
                print(f"已开始模拟跑步，速度大约为 {config.config.v} m/s")
                print("会无限循环，按 Ctrl+C 退出")
                print("请勿直接关闭窗口，否则无法还原正常定位")
                await run.run(loc_sim, loc, config.config.v)


def main():
    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        pass

    if _cleanup_process is not None:
        print("\n正在清除定位...")
        try:
            asyncio.run(_do_clear_location())
        except Exception:
            pass
        _cleanup_process.terminate()
        _cleanup_process.join(timeout=5)
    print("Bye")


if __name__ == "__main__":
    main()
