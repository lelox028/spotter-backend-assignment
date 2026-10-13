from django.test import SimpleTestCase

from routing.services.planner import NoFeasiblePlan, plan_fuel_stops


class PlannerTests(SimpleTestCase):
    def test_hand_worked_plan(self):
        """Route 900 miles, 48-gallon effective tank, 10 MPG:
        start has 48 gallons; arrive mile 300 with 18 gallons and buy
        30 at $3 ($90); arrive mile 600 with 18 gallons and buy 12 at
        $3.50 ($42); arrive at mile 900. Total is 42 gallons and $132.
        """
        stations = [
            (300, 3.0, {'opis_id': 'a', 'name': 'A'}),
            (600, 3.5, {'opis_id': 'b', 'name': 'B'}),
            (800, 2.0, {'opis_id': 'c', 'name': 'C'}),
        ]
        stops, total = plan_fuel_stops(stations, 900, 480, 10)
        self.assertEqual([stop.station['opis_id'] for stop in stops], ['a', 'b'])
        self.assertAlmostEqual(sum(stop.gallons for stop in stops), 42)
        self.assertAlmostEqual(total, 132)

    def test_finish_within_range_has_no_cost(self):
        stops, total = plan_fuel_stops([], 400, 480, 10)
        self.assertEqual(stops, [])
        self.assertEqual(total, 0)

    def test_unreachable_gap_raises(self):
        with self.assertRaises(NoFeasiblePlan):
            plan_fuel_stops([(500, 3, {'opis_id': 'a'})], 1000, 480, 10)

    def test_cheaper_station_at_range_limit_is_selected(self):
        stops, _ = plan_fuel_stops([(480, 2, {'opis_id': 'a'})], 900, 480, 10)
        self.assertEqual(stops[0].station['opis_id'], 'a')

    def test_same_mile_ties_are_deterministic(self):
        stops, _ = plan_fuel_stops([
            (400, 3, {'opis_id': 'b'}),
            (400, 3, {'opis_id': 'a'}),
        ], 700, 480, 10)
        self.assertEqual(stops[0].station['opis_id'], 'a')
