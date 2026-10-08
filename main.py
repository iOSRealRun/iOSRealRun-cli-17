import signal
import logging
import coloredlogs
import os

from driver import connect
from driver import location

from pymobiledevice3.cli.remote import RemoteServiceDiscoveryService
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService

from init import init
from init import tunnel
from init import route

import run

import config


debug = os.environ.get("DEBUG", False)

logger = logging.getLogger(__name__)

# set logging level
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


def run_device(dvt, loc):
    try:
        print(f"已开始模拟跑步，速度大约为 {config.config.v} m/s")
        print("会无限循环，按 Ctrl+C 退出")
        print("请勿直接关闭窗口，否则无法还原正常定位")
        run.run(dvt, loc, config.config.v)
    except KeyboardInterrupt:
        logger.debug("get KeyboardInterrupt (inner)")
    finally:
        logger.debug("Start to clear location")
        location.clear_location(dvt)
        logger.info("Location cleared")


def run_via_tunnel(loc):
    """iOS 17+: 建 tun 隧道 -> RSD -> DVT"""
    logger.info("starting tunnel")
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    process, address, port = tunnel.tunnel()
    signal.signal(signal.SIGINT, original_sigint_handler)
    logger.info("tunnel started")
    try:
        logger.debug(f"tunnel address: {address}, port: {port}")
        with RemoteServiceDiscoveryService((address, port)) as rsd:
            with DvtSecureSocketProxyService(rsd) as dvt:
                run_device(dvt, loc)
    except KeyboardInterrupt:
        logger.debug("get KeyboardInterrupt (outer)")
    finally:
        logger.debug(f"Is process alive? {process.is_alive()}")
        logger.debug("terminating tunnel process")
        process.terminate()
        logger.info("tunnel process terminated")
        print("Bye")


def run_via_lockdown(lockdown, version, loc):
    """iOS 14~16: 免隧道, 挂 DeveloperDiskImage 后直连 lockdown DVT"""
    logger.info(f"iOS {version} 老系统: 免隧道, 挂载开发者镜像后直连 DVT")
    connect.ensure_developer_image(lockdown)
    with DvtSecureSocketProxyService(lockdown) as dvt:
        run_device(dvt, loc)
    print("Bye")


def main():
    # set level
    coloredlogs.install(level=logging.INFO)
    logger.setLevel(logging.INFO)
    if debug:
        logger.setLevel(logging.DEBUG)
        coloredlogs.install(level=logging.DEBUG)

    lockdown, version, major = init.init()
    logger.info("init done")

    # get route
    loc = route.get_route()
    logger.info(f"got route from {config.config.routeConfig}")

    if major >= 17:
        run_via_tunnel(loc)
    else:
        run_via_lockdown(lockdown, version, loc)


if __name__ == "__main__":
    main()
