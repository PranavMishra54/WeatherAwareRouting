from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from routing.services.checkpoints import build_checkpoints, haversine_miles


class CheckpointTests(SimpleTestCase):
    def setUp(self):
        self.path = [(0.0, 0.0), (0.0, 100 / 69.1)]
        self.duration_seconds = 10_000
        self.departure_time = datetime(2026, 11, 2, 8, tzinfo=timezone.utc)

    def test_builds_interval_checkpoints_and_destination(self):
        checkpoints = build_checkpoints(
            self.path, self.duration_seconds, self.departure_time, 25
        )

        self.assertEqual(
            [checkpoint.mile for checkpoint in checkpoints[:-1]],
            [0.0, 25.0, 50.0, 75.0],
        )
        self.assertEqual(len(checkpoints), 5)
        self.assertAlmostEqual(checkpoints[-1].mile, 100, delta=0.2)
        self.assertEqual((checkpoints[-1].lat, checkpoints[-1].lon), self.path[-1])

    def test_etas_increase_and_destination_eta_is_arrival_time(self):
        checkpoints = build_checkpoints(
            self.path, self.duration_seconds, self.departure_time, 25
        )

        self.assertTrue(
            all(
                earlier.eta < later.eta
                for earlier, later in zip(checkpoints, checkpoints[1:])
            )
        )
        self.assertEqual(
            checkpoints[-1].eta,
            self.departure_time + timedelta(seconds=self.duration_seconds),
        )

    def test_segment_miles_sum_to_path_length(self):
        checkpoints = build_checkpoints(
            self.path, self.duration_seconds, self.departure_time, 25
        )
        total_path_miles = haversine_miles(self.path[0], self.path[-1])

        self.assertAlmostEqual(
            sum(checkpoint.segment_miles for checkpoint in checkpoints),
            total_path_miles,
        )

    def test_rejects_unsupported_interval(self):
        with self.assertRaises(ValueError):
            build_checkpoints(
                self.path, self.duration_seconds, self.departure_time, 20
            )

    def test_rejects_path_with_fewer_than_two_points(self):
        with self.assertRaises(ValueError):
            build_checkpoints(
                [self.path[0]],
                self.duration_seconds,
                self.departure_time,
                25,
            )
