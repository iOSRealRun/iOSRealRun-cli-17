import config

from util import route

def get_route():
    with open(config.config.routeConfig) as myFile:
        loc = route.parse_route(myFile.read())
    return loc  
