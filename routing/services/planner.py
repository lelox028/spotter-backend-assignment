from dataclasses import dataclass


EPSILON = 1e-7


class NoFeasiblePlan(Exception):
    pass


@dataclass(frozen=True)
class PlannedStop:
    station: dict
    gallons: float
    cost: float
    route_mile: float


def plan_fuel_stops(stations, total_route_miles, effective_range_miles, mpg):
    ordered = sorted(stations, key=lambda item: (item[0], item[1], item[2].get('opis_id', '')))
    full_tank = effective_range_miles / mpg
    current_mile = 0.0
    current_price = 0.0
    current_station = None
    fuel = full_tank
    stops = []
    total_cost = 0.0

    while total_route_miles - current_mile > EPSILON:
        remaining_miles = total_route_miles - current_mile
        if remaining_miles <= effective_range_miles + EPSILON:
            if fuel * mpg + EPSILON >= remaining_miles:
                break
            purchase = remaining_miles / mpg - fuel
            if current_station is not None and purchase > EPSILON:
                cost = purchase * current_price
                stops.append(PlannedStop(current_station, purchase, cost, current_mile))
                total_cost += cost
            break

        reachable = [
            item for item in ordered
            if item[0] > current_mile + EPSILON
            and item[0] - current_mile <= effective_range_miles + EPSILON
        ]
        if not reachable:
            raise NoFeasiblePlan('No fuel station is reachable before the route exceeds the effective range.')

        cheaper = [item for item in reachable if item[1] < current_price - EPSILON]
        if cheaper:
            next_item = min(cheaper, key=lambda item: (item[0], item[1], item[2].get('opis_id', '')))
            purchase = max(0.0, (next_item[0] - current_mile) / mpg - fuel)
        else:
            next_item = min(reachable, key=lambda item: (item[1], item[0], item[2].get('opis_id', '')))
            purchase = max(0.0, full_tank - fuel)

        if current_station is not None and purchase > EPSILON:
            cost = purchase * current_price
            stops.append(PlannedStop(current_station, purchase, cost, current_mile))
            total_cost += cost
        distance = next_item[0] - current_mile
        fuel -= distance / mpg
        fuel += purchase
        current_mile = next_item[0]
        current_price = next_item[1]
        current_station = next_item[2]

    return stops, total_cost
