import pytest

import main
from init import route


def test_custom_route_path_selection(tmp_path):
    custom_route = tmp_path / "custom-route.txt"
    custom_route.write_text('{"lat": 1, "lng": 2},\n{"lat": 3, "lng": 4}', encoding="utf-8")

    args = main.parse_args(["--route", str(custom_route)])

    assert args.route == str(custom_route)
    assert route.get_route(args.route) == [
        {"lat": 1.0, "lng": 2.0},
        {"lat": 3.0, "lng": 4.0},
    ]


def test_missing_route_path_error(tmp_path, capsys):
    missing_route = tmp_path / "missing-route.txt"

    with pytest.raises(SystemExit):
        main.parse_args(["--route", str(missing_route)])

    assert f"route file not found: {missing_route}" in capsys.readouterr().err


def test_list_routes_is_optional(tmp_path):
    routes_dir = tmp_path / "routes"
    routes_dir.mkdir()
    (routes_dir / "z-route.txt").write_text("", encoding="utf-8")
    (routes_dir / "a-route.txt").write_text("", encoding="utf-8")

    assert route.list_routes(routes_dir) == [routes_dir / "a-route.txt", routes_dir / "z-route.txt"]
