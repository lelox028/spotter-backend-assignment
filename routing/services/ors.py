import requests
from django.conf import settings


ORS_URL = 'https://api.openrouteservice.org/v2/directions/driving-car/geojson'


class RoutingServiceError(Exception):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.status_code = status_code


def get_route(start, finish):
    if not settings.ORS_API_KEY:
        raise RoutingServiceError('Routing service is not configured.', 502)
    try:
        response = requests.post(
            ORS_URL,
            json={'coordinates': [[start['lng'], start['lat']], [finish['lng'], finish['lat']]],
                  'instructions': False},
            headers={
                'Authorization': settings.ORS_API_KEY,
                'Content-Type': 'application/json',
                'Accept': 'application/geo+json, application/json',
            },
            timeout=settings.ORS_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise RoutingServiceError('Routing service timed out.', 504) from exc
    except requests.RequestException as exc:
        raise RoutingServiceError('Routing service is unavailable.', 502) from exc

    if response.status_code >= 500:
        raise RoutingServiceError('Routing service returned a server error.', 502)
    if response.status_code in (401, 403):
        raise RoutingServiceError('Routing service rejected the API key or quota.', 502)
    if response.status_code >= 400:
        raise RoutingServiceError('Routing service rejected the route request.', 502)
    try:
        payload = response.json()
        feature = payload['features'][0]
        coordinates = feature['geometry']['coordinates']
        properties = feature['properties']
        distance_meters = properties.get('summary', {}).get('distance')
        if distance_meters is None:
            distance_meters = sum(
                segment['distance'] for segment in properties['segments']
            )
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise RoutingServiceError('Routing service returned an invalid response.', 502) from exc
    return coordinates, float(distance_meters) * 0.000621371192
