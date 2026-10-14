import unittest
import os
from water_quality_core import WaterQualityAlertSystem, STANDARD_THRESHOLDS

class TestWaterQualityAlertSystem(unittest.TestCase):
    def setUp(self):
        self.system = WaterQualityAlertSystem()

    def test_normal_reading_no_alert(self):
        record = {
            "station_id": "TEST-01",
            "timestamp": "2026-10-15 10:00:00",
            "ph": "7.2",
            "turbidity": "1.2",
            "chlorine": "2.0",
            "temperature": "18.0",
            "dissolved_oxygen": "8.5",
            "lead": "0.002"
        }
        success, err, alerts = self.system.process_record(record)
        self.assertTrue(success)
        self.assertIsNone(err)
        self.assertEqual(len(alerts), 0)

    def test_ph_low_alert(self):
        record = {
            "station_id": "TEST-02",
            "timestamp": "2026-10-15 10:00:00",
            "ph": 5.8,
            "turbidity": 1.0,
            "chlorine": 2.0
        }
        success, err, alerts = self.system.process_record(record)
        self.assertTrue(success)
        self.assertTrue(any(a["metric"] == "ph" and a["severity"] in ["WARNING", "CRITICAL"] for a in alerts))

    def test_lead_critical_alert(self):
        record = {
            "station_id": "TEST-03",
            "timestamp": "2026-10-15 10:00:00",
            "ph": 7.4,
            "turbidity": 2.0,
            "lead": 0.035
        }
        success, err, alerts = self.system.process_record(record)
        self.assertTrue(success)
        lead_alerts = [a for a in alerts if a["metric"] == "lead"]
        self.assertEqual(len(lead_alerts), 1)
        self.assertEqual(lead_alerts[0]["severity"], "CRITICAL")

    def test_error_handling_malformed_data(self):
        # Corrupt pH text
        bad_record = {
            "station_id": "TEST-04",
            "timestamp": "2026-10-15 10:00:00",
            "ph": "INVALID_FLOAT"
        }
        success, err, alerts = self.system.process_record(bad_record)
        self.assertFalse(success)
        self.assertIn("Invalid numeric format", err)
        self.assertGreaterEqual(len(self.system.error_logs), 1)

    def test_csv_ingestion(self):
        stats = self.system.load_from_csv("sensor_telemetry_sample.csv")
        self.assertGreater(stats["total"], 0)
        self.assertGreater(stats["valid"], 0)
        self.assertGreater(len(self.system.sensor_records), 0)

if __name__ == "__main__":
    unittest.main()
