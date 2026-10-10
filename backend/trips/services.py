"""Trip planning rules for property-carrying drivers (70 hours / 8 days)."""

from datetime import datetime, timedelta
import math
import requests

HOURS_PER_DAY = 24
MAX_DRIVING = 11
MAX_ON_DUTY_WINDOW = 14
BREAK_AFTER_DRIVING = 8
BREAK_DURATION = 0.5
OFF_DUTY_RESET = 10
CYCLE_LIMIT = 70
PICKUP_HOURS = 1
DROPOFF_HOURS = 1
FUEL_EVERY_MILES = 1000


def _geocode(place):
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": place, "format": "jsonv2", "limit": 1},
            headers={"User-Agent": "SpotterTripPlanner/1.0"},
            timeout=5,
        )
        item = response.json()[0]
        return {"lat": float(item["lat"]), "lng": float(item["lon"]), "label": place}
    except (requests.RequestException, IndexError, KeyError, TypeError, ValueError):
        return None


def _fallback_point(place, index):
    """Keep common demo locations geographically accurate when geocoding is unavailable."""
    seeds = [
        (32.7767, -96.7970), (29.7604, -95.3698), (33.7490, -84.3880),
        (39.7392, -104.9903), (36.1627, -86.7816), (34.0522, -118.2437),
    ]
    known_places = {
        "new york": (40.7128, -74.0060),
        "dallas": (32.7767, -96.7970),
        "houston": (29.7604, -95.3698),
        "atlanta": (33.7490, -84.3880),
        "los angeles": (34.0522, -118.2437),
        "chicago": (41.8781, -87.6298),
        "new york ny": (40.7128, -74.0060),
        "dallas tx": (32.7767, -96.7970),
        "houston tx": (29.7604, -95.3698),
        "atlanta ga": (33.7490, -84.3880),
        "los angeles ca": (34.0522, -118.2437),
        "chicago il": (41.8781, -87.6298),
    }
    key = " ".join(place.lower().replace(",", " ").split())
    lat, lng = known_places.get(key, seeds[index % len(seeds)])
    return {"lat": lat, "lng": lng, "label": place}


def _distance(a, b):
    radius = 3958.8
    dlat = math.radians(b["lat"] - a["lat"])
    dlng = math.radians(b["lng"] - a["lng"])
    x = math.sin(dlat / 2) ** 2 + math.cos(math.radians(a["lat"])) * math.cos(math.radians(b["lat"])) * math.sin(dlng / 2) ** 2
    return radius * 2 * math.asin(math.sqrt(x))


def _route(points):
    coordinates = [[point["lng"], point["lat"]] for point in points]
    try:
        joined = ";".join(f"{lng},{lat}" for lng, lat in coordinates)
        response = requests.get(
            f"https://router.project-osrm.org/route/v1/driving/{joined}",
            params={"overview": "full", "geometries": "geojson", "steps": "false"},
            timeout=8,
        )
        data = response.json()["routes"][0]
        geometry = [{"lat": lat, "lng": lng} for lng, lat in data["geometry"]["coordinates"]]
        return round(data["distance"] / 1609.344), round(data["duration"] / 3600, 2), geometry, "OSRM"
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
        miles = sum(_distance(points[i], points[i + 1]) for i in range(len(points) - 1))
        geometry = [{"lat": point["lat"], "lng": point["lng"]} for point in points]
        return round(miles), round(miles / 52, 2), geometry, "Estimated"


def _format_time(hour):
    day = int(hour // HOURS_PER_DAY) + 1
    clock = hour % HOURS_PER_DAY
    suffix = "AM" if clock < 12 else "PM"
    display = clock % 12 or 12
    minutes = round((clock - int(clock)) * 60)
    if minutes == 60:
        display += 1
        minutes = 0
    return f"Day {day}, {display}:{minutes:02d} {suffix}"


def _segment(day, start, end, status, label=""):
    return {"day": day, "start": round(start, 2), "end": round(end, 2), "status": status, "label": label}


def build_schedule(total_drive, current_cycle):
    schedule = []
    stops = []
    elapsed = 0.0
    day = 1
    daily_drive = 0.0
    window_start = 0.0
    drive_since_break = 0.0
    cycle_used = current_cycle
    driven = 0.0
    while driven < total_drive:
        if daily_drive >= MAX_DRIVING or elapsed - window_start >= MAX_ON_DUTY_WINDOW or cycle_used >= CYCLE_LIMIT:
            rest = OFF_DUTY_RESET
            schedule.append(_segment(day, elapsed, elapsed + rest, "sleeper", "10-hour reset"))
            stops.append({"type": "rest", "label": "10-hour rest", "atHour": round(elapsed, 2), "time": _format_time(elapsed)})
            elapsed += rest
            day += 1
            daily_drive = 0
            window_start = elapsed
            drive_since_break = 0
            cycle_used = max(0, cycle_used - 10)
            continue
        if drive_since_break >= BREAK_AFTER_DRIVING:
            schedule.append(_segment(day, elapsed, elapsed + BREAK_DURATION, "off_duty", "30-minute break"))
            stops.append({"type": "break", "label": "30-minute break", "atHour": round(elapsed, 2), "time": _format_time(elapsed)})
            elapsed += BREAK_DURATION
            drive_since_break = 0
            cycle_used += BREAK_DURATION
            continue
        available = min(
            MAX_DRIVING - daily_drive,
            MAX_ON_DUTY_WINDOW - (elapsed - window_start),
            CYCLE_LIMIT - cycle_used,
            BREAK_AFTER_DRIVING - drive_since_break,
        )
        # Elapsed includes rest time, so calculate remaining miles as driving time.
        driven = sum(x["end"] - x["start"] for x in schedule if x["status"] == "driving")
        remaining = total_drive - driven
        chunk = min(available, remaining)
        if chunk <= 0.01:
            continue
        schedule.append(_segment(day, elapsed, elapsed + chunk, "driving"))
        elapsed += chunk
        driven += chunk
        daily_drive += chunk
        drive_since_break += chunk
        cycle_used += chunk
        if total_drive - driven <= 0.01:
            break
    return schedule, stops


def plan_trip(payload):
    places = [payload["current_location"], payload["pickup_location"], payload["dropoff_location"]]
    points = [_geocode(place) or _fallback_point(place, i) for i, place in enumerate(places)]
    miles, drive_hours, geometry, provider = _route(points)
    current_cycle = float(payload["current_cycle_used"])
    schedule, stops = build_schedule(drive_hours, current_cycle)
    trip_end = max((x["end"] for x in schedule), default=drive_hours)
    pickup_at = trip_end + 0.01
    schedule.append(_segment(math.floor(pickup_at / HOURS_PER_DAY) + 1, pickup_at, pickup_at + PICKUP_HOURS, "on_duty", "Pickup"))
    dropoff_at = pickup_at + PICKUP_HOURS
    schedule.append(_segment(math.floor(dropoff_at / HOURS_PER_DAY) + 1, dropoff_at, dropoff_at + DROPOFF_HOURS, "on_duty", "Drop-off"))
    fuel_count = max(0, math.ceil(miles / FUEL_EVERY_MILES) - 1)
    for index in range(fuel_count):
        fraction = (index + 1) / (fuel_count + 1)
        stops.append({"type": "fuel", "label": f"Fuel stop {index + 1}", "atHour": round(drive_hours * fraction, 2), "time": _format_time(drive_hours * fraction)})
    days = max(item["day"] for item in schedule)
    logs = []
    for day_number in range(1, days + 1):
        logs.append({"day": day_number, "date": (datetime.utcnow() + timedelta(days=day_number - 1)).strftime("%b %d, %Y"), "segments": [x for x in schedule if x["day"] == day_number]})
    return {
        "summary": {"distanceMiles": miles, "drivingHours": round(drive_hours, 1), "days": days, "cycleRemaining": round(max(0, CYCLE_LIMIT - current_cycle - drive_hours), 1), "routingProvider": provider},
        "points": points,
        "geometry": geometry,
        "stops": sorted(stops, key=lambda item: item["atHour"]),
        "schedule": schedule,
        "dailyLogs": logs,
        "assumptions": {"cycleLimit": "70 hours / 8 days", "maxDrivingPerDay": "11 hours", "dutyWindow": "14 hours", "pickupHours": 1, "dropoffHours": 1},
    }
