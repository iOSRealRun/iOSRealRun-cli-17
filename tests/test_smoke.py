import random
import sys
import threading
import unittest
from pathlib import Path

from run import build_lap_schedule, geodistance
from util.console_guard import install_console_close_handler
from util.route import parse_route


class SmokeTests(unittest.TestCase):
    def test_non_windows_console_guard_is_noop(self):
        original_platform = sys.platform
        sys.platform = "darwin"
        try:
            uninstall = install_console_close_handler(
                lambda: None, threading.Event()
            )
            uninstall()
        finally:
            sys.platform = original_platform

    def test_smooth_speed_preserves_average(self):
        route_text = Path("HNroute.txt").read_text(encoding="utf-8")
        route = parse_route(route_text)
        points, interval = build_lap_schedule(
            route,
            v=3.3,
            dt=0.2,
            speed_variation=0.05,
            rng=random.Random(123),
        )
        sampled_distance = sum(
            geodistance(points[index], points[(index + 1) % len(points)])
            for index in range(len(points))
        )
        average_speed = sampled_distance / (len(points) * interval)
        self.assertAlmostEqual(average_speed, 3.3, places=9)


if __name__ == "__main__":
    unittest.main()
