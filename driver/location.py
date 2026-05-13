from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation


async def set_location(dvt, lat: float, lng: float):
    async with LocationSimulation(dvt) as loc:
        await loc.set(lat, lng)


async def clear_location(dvt):
    async with LocationSimulation(dvt) as loc:
        await loc.clear()
