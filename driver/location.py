from pymobiledevice3.cli.developer import LocationSimulation

def set_location(dvt, lat: float, lng: float):
    LocationSimulation(dvt).set(lat, lng)

def clear_location(dvt):
    LocationSimulation(dvt).clear()
