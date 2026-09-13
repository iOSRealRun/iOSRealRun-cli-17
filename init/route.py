from pathlib import Path

import config
from util import route


def validate_route_path(path: str | Path) -> Path:
    """Validate and return a route file path without changing its route format."""
    route_path = Path(path).expanduser()
    if not route_path.exists():
        raise FileNotFoundError(f"route file not found: {route_path}")
    if not route_path.is_file():
        raise ValueError(f"route path is not a file: {route_path}")
    return route_path


def get_route(path: str | Path | None = None):
    route_path = validate_route_path(path or config.config.routeConfig)
    with route_path.open(encoding="utf-8") as route_file:
        return route.parse_route(route_file.read())


def list_routes(directory: str | Path = "routes") -> list[Path]:
    """Return regular route files from the optional routes directory."""
    routes_path = Path(directory).expanduser()
    if not routes_path.is_dir():
        return []
    return sorted(
        path for path in routes_path.iterdir() if path.is_file() and not path.name.startswith(".")
    )
