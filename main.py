import asyncio
from contextlib import suppress
import logging
import os
import threading

from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

from driver import location
from init import init
from init import route
from init import tunnel
from util.console_guard import install_console_close_handler

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
                    loop = asyncio.get_running_loop()
                    stop_event = asyncio.Event()
                    cleanup_done = threading.Event()

                    def request_shutdown():
                        if not loop.is_closed():
                            loop.call_soon_threadsafe(stop_event.set)

                    uninstall = install_console_close_handler(request_shutdown, cleanup_done)
                    runner = None
                    stopper = None
                    try:
                        logger.info("clearing any previous simulated location")
                        await location.clear_location(simulation)

                        loc = route.get_route()
                        logger.info("got route from %s", config.config.routeConfig)

                        speed_variation = float(
                            getattr(config.config, "speedVariation", 0.05)
                        )
                        if not 0 <= speed_variation < 1:
                            raise ValueError(
                                "speedVariation must be between 0 (inclusive) and 1"
                            )
                        variation_percent = speed_variation * 100
                        print(
                            f"已开始模拟跑步，平均速度为 {config.config.v} m/s，"
                            f"实时速度波动约 ±{variation_percent:g}%"
                        )
                        print("会无限循环，按 Ctrl+C 退出")
                        print("直接关闭窗口时会尝试自动恢复定位；强制结束进程仍建议重启手机")

                        runner = asyncio.create_task(
                            run.run(simulation, loc, config.config.v, speed_variation)
                        )
                        stopper = asyncio.create_task(stop_event.wait())
                        done, _ = await asyncio.wait({runner, stopper}, return_when=asyncio.FIRST_COMPLETED)

                        if runner in done:
                            runner.result()
                        else:
                            runner.cancel()
                            with suppress(asyncio.CancelledError):
                                await runner
                    finally:
                        if stopper is not None:
                            stopper.cancel()
                            with suppress(asyncio.CancelledError):
                                await stopper
                        if runner is not None and not runner.done():
                            runner.cancel()
                            with suppress(asyncio.CancelledError):
                                await runner
                        try:
                            logger.info("start to clear location")
                            await location.clear_location(simulation)
                            logger.info("Location cleared")
                        finally:
                            cleanup_done.set()
                            uninstall()
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
