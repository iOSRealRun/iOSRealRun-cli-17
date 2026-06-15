def set_location(location_client, lat: float, lng: float):
    location_client.set(lat, lng)


def clear_location(location_client):
    location_client.clear()
