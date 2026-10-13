import json
from unittest.mock import patch
from pathlib import Path

from django.test import Client, TestCase

from routing.models import FuelStation
from routing.services.stations import clear_station_cache


class ViewTests(TestCase):
    def setUp(self):
        FuelStation.objects.create(
            opis_id='1', name='Station', address='I-80', city='Test',
            state='NE', price=3.0, lat=40.0, lng=-99.5,
        )
        clear_station_cache()
        self.client = Client()

    def tearDown(self):
        clear_station_cache()

    def test_invalid_input(self):
        response = self.client.post('/api/route/', '{}', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    @patch('routing.views.get_route')
    def test_happy_path_uses_fixture_shape(self, get_route):
        fixture = json.loads(
            (Path(__file__).parent / 'fixtures' / 'ors_route.json').read_text()
        )
        get_route.return_value = (
            fixture['features'][0]['geometry']['coordinates'],
            fixture['features'][0]['properties']['segments'][0]['distance'] * 0.000621371192,
        )
        response = self.client.post(
            '/api/route/',
            {'start': {'lat': 40, 'lng': -100}, 'finish': {'lat': 40, 'lng': -99}},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['route']['type'], 'FeatureCollection')
        self.assertEqual(body['total_fuel_cost'], 0)
        self.assertIn('X-Processing-Time-ms', response)

    @patch('routing.views.get_route')
    def test_ors_failure_is_json_error(self, get_route):
        from routing.services.ors import RoutingServiceError
        get_route.side_effect = RoutingServiceError('timed out', 504)
        response = self.client.post(
            '/api/route/',
            {'start': {'lat': 40, 'lng': -100}, 'finish': {'lat': 40, 'lng': -99}},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json(), {'error': 'timed out'})
