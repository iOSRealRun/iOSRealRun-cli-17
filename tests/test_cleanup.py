import asyncio

import pytest

import main


class FakeLocationSimulation:
    def __init__(self, dvt):
        self.events = []

    async def __aenter__(self):
        self.events.append("open")
        return self

    async def __aexit__(self, *args):
        self.events.append("close")

    async def clear(self):
        self.events.append("clear")


def test_location_is_cleared_on_ctrl_c(monkeypatch, caplog):
    simulation = None

    class Simulation(FakeLocationSimulation):
        def __init__(self, dvt):
            nonlocal simulation
            super().__init__(dvt)
            simulation = self

    async def stop_on_ctrl_c(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(main.location, "LocationSimulation", Simulation)
    monkeypatch.setattr(main.run, "run", stop_on_ctrl_c)
    caplog.set_level("INFO")

    asyncio.run(main.simulate_route(object(), [], 3.3))

    assert simulation.events == ["open", "clear", "close"]
    assert "Simulated location cleared; the device may take a few seconds" in caplog.text


def test_location_is_cleared_on_cancellation(monkeypatch):
    simulation = None

    class Simulation(FakeLocationSimulation):
        def __init__(self, dvt):
            nonlocal simulation
            super().__init__(dvt)
            simulation = self

    async def cancel(*args):
        raise asyncio.CancelledError

    monkeypatch.setattr(main.location, "LocationSimulation", Simulation)
    monkeypatch.setattr(main.run, "run", cancel)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(main.simulate_route(object(), [], 3.3))

    assert simulation.events == ["open", "clear", "close"]
