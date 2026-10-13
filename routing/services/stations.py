from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from routing.models import FuelStation


@dataclass(frozen=True)
class StationSnapshot:
    coordinates: np.ndarray
    metadata: tuple[dict, ...]


@lru_cache(maxsize=1)
def load_stations():
    rows = list(FuelStation.objects.values(
        'opis_id', 'name', 'address', 'city', 'state', 'price', 'lat', 'lng',
    ))
    coordinates = np.array(
        [[row['lng'], row['lat']] for row in rows], dtype=float
    ).reshape((-1, 2))
    return StationSnapshot(coordinates, tuple(rows))


def clear_station_cache():
    load_stations.cache_clear()
