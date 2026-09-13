import logging

from pymobiledevice3.services.dvt.instruments.location_simulation import (
    LocationSimulation,
)

logger = logging.getLogger(__name__)
CLEAR_SUCCESS_MESSAGE = (
    "Simulated location cleared; the device may take a few seconds to reacquire its real location."
)


async def set_location(simulation: LocationSimulation, lat: float, lng: float):
    logger.debug("setting simulated location: latitude=%s longitude=%s", lat, lng)
    await simulation.set(lat, lng)


async def clear_location(simulation: LocationSimulation):
    logger.info("clearing simulated location")
    await simulation.clear()
    logger.info(CLEAR_SUCCESS_MESSAGE)
