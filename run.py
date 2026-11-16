"""
run.py
automatically run the route
"""

"""修正坐标误差，百度取点使用 BD-09 坐标系，iOS使用 WGS-09 坐标系，进行转换"""
import asyncio
import bisect
import math
import time
import random

from geopy.distance import geodesic

from driver import location

def bd09Towgs84(position):
    wgs_p = {}

    x_pi = 3.14159265358979324 * 3000.0 / 180.0
    pi = 3.141592653589793238462643383  # π
    a = 6378245.0  # 长半轴
    ee = 0.00669342162296594323  # 偏心率平方

    def transform_lat(x, y):
        ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * pi) + 20.0 * math.sin(2.0 * x * pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(y * pi) + 40.0 * math.sin(y / 3.0 * pi)) * 2.0 / 3.0
        ret += (160.0 * math.sin(y / 12.0 * pi) + 320 * math.sin(y * pi / 30.0)) * 2.0 / 3.0
        return ret

    def transform_lon(x, y):
        ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * pi) + 20.0 * math.sin(2.0 * x * pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(x * pi) + 40.0 * math.sin(x / 3.0 * pi)) * 2.0 / 3.0
        ret += (150.0 * math.sin(x / 12.0 * pi) + 300.0 * math.sin(x / 30.0 * pi)) * 2.0 / 3.0
        return ret

    x = position['lng'] - 0.0065
    y = position['lat'] - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * x_pi)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * x_pi)

    gcj_lng = z * math.cos(theta)
    gcj_lat = z * math.sin(theta)

    d_lat = transform_lat(gcj_lng - 105.0, gcj_lat - 35.0)
    d_lng = transform_lon(gcj_lng - 105.0, gcj_lat - 35.0)

    rad_lat = gcj_lat / 180.0 * pi
    magic = math.sin(rad_lat)
    magic = 1 - ee * magic * magic
    sqrt_magic = math.sqrt(magic)

    d_lng = (d_lng * 180.0) / (a / sqrt_magic * math.cos(rad_lat) * pi)
    d_lat = (d_lat * 180.0) / (a * (1 - ee) / (magic * sqrt_magic) * pi)

    wgs_p["lat"] = gcj_lat * 2 - gcj_lat - d_lat
    wgs_p["lng"] = gcj_lng * 2 - gcj_lng - d_lng
    return wgs_p

# get the ditance according to the latitude and longitude
def geodistance(p1, p2):
    return geodesic((p1["lat"],p1["lng"]),(p2["lat"],p2["lng"])).m

def smooth(start, end, i):
    import math
    i = (i-start)/(end-start)*math.pi
    return math.sin(i)**2

def randLoc(loc: list, d=0.000025, n=5, rng=None):
    rng = rng or random
    # deepcopy loc
    result = []
    for i in loc:
        result.append(i.copy())

    center = {"lat": 0, "lng": 0}
    for i in result:
        center["lat"] += i["lat"]
        center["lng"] += i["lng"]
    center["lat"] /= len(result)
    center["lng"] /= len(result)
    for i in range(n):
        start = int(i*len(result)/n)
        end = int((i+1)*len(result)/n)
        offset = (2*rng.random()-1) * d
        for j in range(start, end):
            distance = math.sqrt(
                (result[j]["lat"]-center["lat"])**2 + (result[j]["lng"]-center["lng"])**2
            )
            if 0 == distance:
                continue
            result[j]["lat"] +=  (result[j]["lat"]-center["lat"])/distance*offset*smooth(start, end, j)
            result[j]["lng"] +=  (result[j]["lng"]-center["lng"])/distance*offset*smooth(start, end, j)
    start = int(i*len(result)/n)
    end = len(result)
    offset = (2*rng.random()-1) * d
    for j in range(start, end):
        distance = math.sqrt(
            (result[j]["lat"]-center["lat"])**2 + (result[j]["lng"]-center["lng"])**2
        )
        if 0 == distance:
            continue
        result[j]["lat"] +=  (result[j]["lat"]-center["lat"])/distance*offset*smooth(start, end, j)
        result[j]["lng"] +=  (result[j]["lng"]-center["lng"])/distance*offset*smooth(start, end, j)
    return result

def build_route_segments(loc):
    """Return non-zero route segments and the closed route's total length."""
    segments = []
    route_distance = 0.0
    for start, end in zip(loc, loc[1:] + loc[:1]):
        segment_distance = geodistance(start, end)
        if segment_distance == 0:
            continue
        segment_end = route_distance + segment_distance
        segments.append((start, end, route_distance, segment_end))
        route_distance = segment_end
    if not segments or route_distance == 0:
        raise ValueError("route must contain at least two different points")
    return segments, route_distance

def point_at_distance(segments, segment_ends, route_distance, distance):
    distance = min(max(distance, 0.0), route_distance)
    index = min(bisect.bisect_right(segment_ends, distance), len(segments) - 1)
    start, end, segment_start, segment_end = segments[index]
    ratio = (distance - segment_start) / (segment_end - segment_start)
    return {
        "lat": start["lat"] + ratio * (end["lat"] - start["lat"]),
        "lng": start["lng"] + ratio * (end["lng"] - start["lng"]),
    }

def speed_multipliers(step_count, lap_duration, speed_variation, rng):
    """Build a smooth speed curve whose arithmetic mean is exactly one."""
    if speed_variation <= 0:
        return [1.0] * step_count

    # Integer cycle counts keep the speed continuous when the route wraps.
    cycles1 = max(1, round(lap_duration / rng.uniform(18, 45)))
    cycles2 = max(2, round(lap_duration / rng.uniform(12, 30)))
    phase1 = rng.uniform(0, 2 * math.pi)
    phase2 = rng.uniform(0, 2 * math.pi)
    wave = [
        math.sin(2 * math.pi * cycles1 * (i + 0.5) / step_count + phase1)
        + 0.55 * math.sin(2 * math.pi * cycles2 * (i + 0.5) / step_count + phase2)
        for i in range(step_count)
    ]
    mean = sum(wave) / step_count
    wave = [value - mean for value in wave]
    peak = max(abs(value) for value in wave)
    if peak == 0:
        return [1.0] * step_count
    return [1.0 + speed_variation * value / peak for value in wave]

def build_lap_schedule(loc, v, dt, speed_variation, rng):
    """Return paced points and the duration of one constant-time interval."""
    if v <= 0:
        raise ValueError("average speed must be greater than zero")
    if dt <= 0:
        raise ValueError("location interval must be greater than zero")
    if not 0 <= speed_variation < 1:
        raise ValueError("speed variation must be between 0 (inclusive) and 1")

    segments, route_distance = build_route_segments(loc)
    segment_ends = [segment[3] for segment in segments]
    nominal_duration = route_distance / v
    step_count = max(2, math.ceil(nominal_duration / dt))
    multipliers = speed_multipliers(
        step_count, nominal_duration, speed_variation, rng
    )

    def schedule_points(multipliers):
        total = sum(multipliers)
        points = []
        travelled = 0.0
        for multiplier in multipliers:
            distance = route_distance * travelled / total
            points.append(
                point_at_distance(segments, segment_ends, route_distance, distance)
            )
            travelled += multiplier
        return points

    points = schedule_points(multipliers)

    # Interpolating in latitude/longitude makes the sum of sampled geodesic
    # distances differ slightly from the waypoint total. Calibrate the lap
    # duration against the actual sampled path so its average speed stays v.
    sampled_distance = sum(
        geodistance(points[i], points[(i + 1) % step_count])
        for i in range(step_count)
    )
    calibrated_steps = max(2, math.ceil((sampled_distance / v) / dt))
    if calibrated_steps != step_count:
        step_count = calibrated_steps
        multipliers = speed_multipliers(
            step_count, sampled_distance / v, speed_variation, rng
        )
        points = schedule_points(multipliers)
        sampled_distance = sum(
            geodistance(points[i], points[(i + 1) % step_count])
            for i in range(step_count)
        )

    interval = sampled_distance / (v * step_count)
    return points, interval

async def run1(simulation, loc: list, v, dt=0.2, speed_variation=0.0, rng=None):
    rng = rng or random
    nList = (5, 6, 7, 8, 9)
    n = nList[rng.randint(0, len(nList)-1)]
    route_points = randLoc(loc, n=n, rng=rng)
    points, interval = build_lap_schedule(route_points, v, dt, speed_variation, rng)
    lap_started = time.monotonic()
    for index, point in enumerate(points):
        await location.set_location(simulation, **bd09Towgs84(point))
        deadline = lap_started + (index + 1) * interval
        remaining = deadline - time.monotonic()
        if remaining > 0:
            await asyncio.sleep(remaining)


async def run(simulation, loc: list, v, speed_variation=0.05):
    rng = random.Random(time.time_ns())
    while True:
        await run1(simulation, loc, v, speed_variation=speed_variation, rng=rng)
        print("跑完一圈了")
