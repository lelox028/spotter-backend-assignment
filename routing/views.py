import json
import time

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services.geo import stations_in_corridor
from .services.ors import RoutingServiceError, get_route
from .services.planner import NoFeasiblePlan, plan_fuel_stops
from .services.stations import load_stations


MIN_LAT, MAX_LAT = 24.5, 49.5
MIN_LNG, MAX_LNG = -125.0, -66.9


def _error(message, status):
    return JsonResponse({'error': message}, status=status)


def _coordinate(value, name):
    if not isinstance(value, dict):
        raise ValueError(f'{name} must be an object.')
    lat, lng = value.get('lat'), value.get('lng')
    if isinstance(lat, bool) or isinstance(lng, bool) or not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        raise ValueError(f'{name}.lat and {name}.lng must be numbers.')
    if not MIN_LAT <= lat <= MAX_LAT or not MIN_LNG <= lng <= MAX_LNG:
        raise ValueError(f'{name} is outside the contiguous-USA bounding box.')
    return {'lat': float(lat), 'lng': float(lng)}


@csrf_exempt
@require_POST
def route_view(request):
    started = time.perf_counter()
    try:
        payload = json.loads(request.body)
        start = _coordinate(payload['start'], 'start')
        finish = _coordinate(payload['finish'], 'finish')
    except (json.JSONDecodeError, TypeError, KeyError, ValueError):
        return _error('Request body must contain valid start and finish coordinates.', 400)

    try:
        coordinates, total_distance = get_route(start, finish)
    except RoutingServiceError as exc:
        return _error(str(exc), exc.status_code)

    snapshot = load_stations()
    corridor_stations = stations_in_corridor(
        coordinates, snapshot.coordinates, settings.CORRIDOR_MILES
    )
    planner_input = [
        (mile, snapshot.metadata[index]['price'], snapshot.metadata[index])
        for index, mile in corridor_stations
    ]
    try:
        stops, total_cost = plan_fuel_stops(
            planner_input,
            total_distance,
            settings.EFFECTIVE_RANGE_MILES,
            settings.MPG,
        )
    except NoFeasiblePlan as exc:
        return _error(str(exc), 422)

    features = [{
        'type': 'Feature',
        'properties': {'kind': 'route'},
        'geometry': {'type': 'LineString', 'coordinates': coordinates},
    }]
    for stop in stops:
        station = stop.station
        features.append({
            'type': 'Feature',
            'properties': {
                'kind': 'fuel_stop',
                'name': station['name'],
                'address': station['address'],
                'city': station['city'],
                'state': station['state'],
                'price_per_gallon': station['price'],
                'gallons_purchased': stop.gallons,
                'cost': stop.cost,
                'route_mile': stop.route_mile,
            },
            'geometry': {'type': 'Point', 'coordinates': [station['lng'], station['lat']]},
        })

    response = JsonResponse({
        'route': {'type': 'FeatureCollection', 'features': features},
        'total_distance_miles': total_distance,
        'total_gallons': sum(stop.gallons for stop in stops),
        'total_fuel_cost': total_cost,
    })
    response['X-Processing-Time-ms'] = f'{(time.perf_counter() - started) * 1000:.2f}'
    return response

# Create your views here.
