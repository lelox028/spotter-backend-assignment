import numpy as np


EARTH_RADIUS_MILES = 3958.8


def _project(coordinates, origin_lng, origin_lat):
    coordinates = np.asarray(coordinates, dtype=float)
    scale = np.cos(np.radians(origin_lat))
    x = np.radians(coordinates[:, 0] - origin_lng) * EARTH_RADIUS_MILES * scale
    y = np.radians(coordinates[:, 1] - origin_lat) * EARTH_RADIUS_MILES
    return np.column_stack((x, y))


def route_miles(route_coordinates):
    points = np.asarray(route_coordinates, dtype=float)
    if len(points) < 2:
        return np.array([0.0])
    projected = _project(points, points[0, 0], points[0, 1])
    segments = np.diff(projected, axis=0)
    distances = np.sqrt((segments * segments).sum(axis=1))
    return np.concatenate(([0.0], np.cumsum(distances)))


def stations_in_corridor(route_coordinates, station_coordinates, corridor_miles):
    route = np.asarray(route_coordinates, dtype=float)
    stations = np.asarray(station_coordinates, dtype=float)
    if len(route) < 2 or len(stations) == 0:
        return []

    route_distances = route_miles(route)
    margin_lat = corridor_miles / 69.0
    margin_lng = corridor_miles / (69.0 * max(np.cos(np.radians(route[:, 1])).min(), 0.1))
    lower = np.array([route[:, 0].min() - margin_lng, route[:, 1].min() - margin_lat])
    upper = np.array([route[:, 0].max() + margin_lng, route[:, 1].max() + margin_lat])
    candidates = np.flatnonzero(np.all((stations >= lower) & (stations <= upper), axis=1))
    if len(candidates) == 0:
        return []

    origin = route[0]
    route_xy = _project(route, origin[0], origin[1])
    station_xy = _project(stations[candidates], origin[0], origin[1])
    best_distance = np.full(len(candidates), np.inf)
    best_mile = np.zeros(len(candidates))
    for index in range(len(route) - 1):
        start = route_xy[index]
        vector = route_xy[index + 1] - start
        length_sq = float(np.dot(vector, vector))
        if length_sq == 0:
            projection = np.zeros(len(candidates))
        else:
            projection = np.clip(((station_xy - start) @ vector) / length_sq, 0.0, 1.0)
        nearest = start + projection[:, None] * vector
        distances = np.sqrt(((station_xy - nearest) ** 2).sum(axis=1))
        improved = distances < best_distance
        best_distance[improved] = distances[improved]
        best_mile[improved] = route_distances[index] + projection[improved] * (
            route_distances[index + 1] - route_distances[index]
        )

    return [(int(index), float(best_mile[position])) for position, index in enumerate(candidates)
            if best_distance[position] <= corridor_miles + 1e-9]
