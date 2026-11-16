async def set_location(simulation, lat: float, lng: float):
    await simulation.set(lat, lng)


async def clear_location(simulation):
    await simulation.clear()
