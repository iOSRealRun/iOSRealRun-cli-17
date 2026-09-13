import argparse
import asyncio
import logging
import os

import coloredlogs
from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider

import config
import run
from driver import location
from init import init, route, tunnel

logger = logging.getLogger(__name__)


def configure_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    coloredlogs.install(level=level)
    for logger_name in (
        "wintun",
        "quic",
        "asyncio",
        "zeroconf",
        "parso.cache",
        "parso.cache.pickle",
        "parso.python.diff",
        "humanfriendly.prompts",
        "blib2to3.pgen2.driver",
        "urllib3.connectionpool",
    ):
        logging.getLogger(logger_name).setLevel(level if debug else logging.WARNING)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Simulate an iOS location along a route")
    parser.add_argument("--udid", help="target a specific USB device")
    parser.add_argument(
        "--route",
        default=config.config.routeConfig,
        metavar="PATH",
        help=f"route file to simulate (default: {config.config.routeConfig})",
    )
    parser.add_argument(
        "--list-routes",
        action="store_true",
        help="list route files in the optional routes/ directory and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="connect, validate Developer Mode, open RSD/DVT, then exit",
    )
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="run diagnostic connection checks and exit",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="enable verbose pymobiledevice3 and connection logging",
    )
    args = parser.parse_args(argv)
    if args.dry_run and args.diagnostic:
        parser.error("--dry-run and --diagnostic are mutually exclusive")
    if not args.list_routes:
        try:
            args.route = str(route.validate_route_path(args.route))
        except (FileNotFoundError, ValueError) as error:
            parser.error(str(error))
    return args


async def simulate_route(dvt, loc, speed) -> None:
    print(f"已开始模拟跑步，速度大约为 {speed} m/s")
    print("会无限循环，按 Ctrl+C 退出")
    print("请勿直接关闭窗口，否则无法还原正常定位")

    async with location.LocationSimulation(dvt) as simulation:
        try:
            await run.run(simulation, loc, speed)
        except KeyboardInterrupt:
            logger.info("Ctrl+C received; stopping route simulation")
        finally:
            try:
                await location.clear_location(simulation)
            except Exception:
                logger.exception("failed to clear simulated location")


async def async_main(args) -> None:
    if args.list_routes:
        available_routes = route.list_routes()
        if available_routes:
            for available_route in available_routes:
                print(available_route)
        else:
            print("No route files found in routes/.")
        return

    device = await init.init(serial=args.udid)
    logger.info("device initialization complete (iOS %s, UDID %s)", device.version, device.udid)

    # AdaptiveRsdTunnel keeps either the userspace tunnel or the tunneld-backed
    # RSD alive for the common DVT layer.
    tunnel_handle = tunnel.create(serial=args.udid or device.udid)
    async with tunnel_handle as rsd:
        logger.info(
            "RSD connection established (backend=%s, in-process=%s, iOS=%s)",
            tunnel_handle.backend,
            rsd.is_in_process_tunnel,
            rsd.product_version,
        )
        async with DvtProvider(rsd) as dvt:
            logger.info("DVT connection established")
            if args.diagnostic:
                logger.info("diagnostic checks complete; route simulation was not started")
                print(
                    "Diagnostic checks succeeded "
                    f"(backend: {tunnel_handle.backend}); route simulation was not started."
                )
                return
            if args.dry_run:
                logger.info("dry-run complete; route simulation was not started")
                print(
                    "Dry run succeeded "
                    f"(backend: {tunnel_handle.backend}); route simulation was not started."
                )
                return

            loc = route.get_route(args.route)
            logger.info("got route from %s", args.route)
            await simulate_route(dvt, loc, config.config.v)


def main(argv=None) -> None:
    args = parse_args(argv)
    debug = args.debug or bool(os.environ.get("DEBUG"))
    configure_logging(debug)
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        logger.info("interrupted; tunnel and service contexts are closing")
    print("Bye")


if __name__ == "__main__":
    main()
