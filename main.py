import asyncio
import logging
import os

from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

from driver import location
from init import init
from init import route
from init import tunnel

import run
import config


debug = os.environ.get("DEBUG", False)
logging.basicConfig(
    level=logging.DEBUG if debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
for noisy_logger in (
    "asyncio",
    "quic",
    "zeroconf",
    "parso.cache",
    "parso.cache.pickle",
    "parso.python.diff",
    "urllib3.connectionpool",
):
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def main_async():
    lockdown = await init.init()
    logger.info("init done")

    try:
        logger.info("starting userspace tunnel")
        async with tunnel.tunnel(serial=lockdown.udid) as rsd:
            logger.info(
                "tunnel connected: %s iOS %s",
                getattr(rsd, "product_type", "unknown"),
                getattr(rsd, "product_version", "unknown"),
            )

            async with DvtProvider(rsd) as dvt:
                async with LocationSimulation(dvt) as simulation:
                    loc = route.get_route()
                    logger.info("got route from %s", config.config.routeConfig)

                    print(f"已开始模拟跑步，速度大约为 {config.config.v} m/s")
                    print("会无限循环，按 Ctrl+C 退出")
                    print("请勿直接关闭窗口，否则无法还原正常定位")

                    try:
                        await run.run(simulation, loc, config.config.v)
                    finally:
                        logger.info("start to clear location")
                        await location.clear_location(simulation)
                        logger.info("Location cleared")
    finally:
        await lockdown.close()


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        print("Bye")


if __name__ == "__main__":
    main()
