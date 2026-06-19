async def set_location(location_simulation, lat: float, lng: float):
    await location_simulation.set(lat, lng)

async def clear_location(location_simulation):
    await location_simulation.clear()
