import json
from unittest.mock import patch

from django.test import TestCase, Client

from .services import _fallback_point, build_schedule, plan_trip


class TripPlanningTests(TestCase):
    def setUp(self):
        self.payload = {
            "current_location": "Dallas, TX",
            "pickup_location": "Houston, TX",
            "dropoff_location": "Atlanta, GA",
            "current_cycle_used": 20,
        }

    def test_known_fallback_locations_preserve_city_coordinates(self):
        new_york = _fallback_point("New York, NY", 0)
        dallas = _fallback_point("Dallas, TX", 0)
        self.assertNotEqual(new_york["lat"], dallas["lat"])
        self.assertAlmostEqual(new_york["lat"], 40.7128)
        self.assertAlmostEqual(new_york["lng"], -74.0060)

    def test_schedule_preserves_driving_and_adds_breaks_and_resets(self):
        schedule, stops = build_schedule(25, 20)
        driving = sum(item["end"] - item["start"] for item in schedule if item["status"] == "driving")
        self.assertAlmostEqual(driving, 25)
        self.assertTrue(any(stop["type"] == "break" for stop in stops))
        self.assertTrue(any(stop["type"] == "rest" for stop in stops))

    @patch("trips.services._geocode")
    @patch("trips.services._route")
    def test_plan_trip_returns_multi_day_logs_and_fuel_stop(self, route, geocode):
        geocode.side_effect = lambda place: _fallback_point(place, 0)
        route.return_value = (1200, 24, [
            {"lat": 32.7767, "lng": -96.7970},
            {"lat": 40.7128, "lng": -74.0060},
        ], "Test route")
        result = plan_trip(self.payload)
        self.assertEqual(result["summary"]["distanceMiles"], 1200)
        self.assertGreaterEqual(len(result["dailyLogs"]), 2)
        self.assertTrue(any(stop["type"] == "fuel" for stop in result["stops"]))

    def test_api_rejects_invalid_cycle(self):
        response = Client().post(
            "/api/trip-plan/",
            data=json.dumps({**self.payload, "current_cycle_used": 71}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
