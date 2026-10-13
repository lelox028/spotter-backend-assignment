from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from routing.services.ors import ORS_URL, RoutingServiceError, get_route


class OrsTests(SimpleTestCase):
    @override_settings(ORS_API_KEY='test-key')
    @patch('routing.services.ors.requests.post')
    def test_geojson_request_and_distance_conversion(self, post):
        response = Mock(status_code=200)
        response.json.return_value = {
            'features': [{
                'geometry': {'coordinates': [[-75, 40], [-74, 41]]},
                'properties': {'segments': [{'distance': 1609.344}]},
            }]
        }
        post.return_value = response
        coordinates, miles = get_route({'lat': 40, 'lng': -75}, {'lat': 41, 'lng': -74})
        self.assertEqual(coordinates, [[-75, 40], [-74, 41]])
        self.assertAlmostEqual(miles, 1)
        kwargs = post.call_args.kwargs
        self.assertEqual(post.call_args.args[0], ORS_URL)
        self.assertEqual(kwargs['json']['coordinates'], [[-75, 40], [-74, 41]])
        self.assertEqual(kwargs['headers']['Authorization'], 'test-key')
        self.assertTrue(kwargs['timeout'])

    @override_settings(ORS_API_KEY='test-key')
    @patch('routing.services.ors.requests.post', side_effect=__import__('requests').Timeout)
    def test_timeout_maps_to_504(self, post):
        with self.assertRaises(RoutingServiceError) as context:
            get_route({'lat': 40, 'lng': -75}, {'lat': 41, 'lng': -74})
        self.assertEqual(context.exception.status_code, 504)
