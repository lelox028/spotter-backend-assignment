from django.test import SimpleTestCase

from routing.services.geo import route_miles, stations_in_corridor


class GeoTests(SimpleTestCase):
    def test_route_miles_and_corridor_projection(self):
        route = [[-100.0, 35.0], [-99.0, 35.0], [-98.0, 35.0]]
        stations = [[-99.5, 35.05], [-98.0, 36.0], [-101.0, 35.0]]
        matches = stations_in_corridor(route, stations, 10)
        self.assertEqual([index for index, _ in matches], [0])
        self.assertAlmostEqual(matches[0][1], route_miles(route)[1] / 2, delta=1)
