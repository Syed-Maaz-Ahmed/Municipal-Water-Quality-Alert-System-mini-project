import csv
import json
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

# EPA / WHO Standard Thresholds for Municipal Drinking Water
STANDARD_THRESHOLDS = {
    "ph": {
        "min": 6.5,
        "max": 8.5,
        "unit": "pH",
        "description": "Acidity / Basicity (safe: 6.5 - 8.5)"
    },
    "turbidity": {
        "min": 0.0,
        "max": 5.0,  # NTU; ideal < 1.0, threshold alert > 5.0
        "unit": "NTU",
        "description": "Cloudiness / Suspended Particles (safe <= 5.0 NTU)"
    },
    "chlorine": {
        "min": 0.2,  # Residual disinfectant needed
        "max": 4.0,  # Maximum residual disinfectant level
        "unit": "mg/L",
        "description": "Free Chlorine Disinfectant (safe: 0.2 - 4.0 mg/L)"
    },
    "temperature": {
        "min": 4.0,
        "max": 25.0,
        "unit": "°C",
        "description": "Water Temperature (safe: 4.0 - 25.0 °C)"
    },
    "dissolved_oxygen": {
        "min": 6.0,
        "max": 14.0,
        "unit": "mg/L",
        "description": "Dissolved Oxygen (safe >= 6.0 mg/L)"
    },
    "lead": {
        "min": 0.0,
        "max": 0.015,
        "unit": "mg/L",
        "description": "Lead Contamination (Action level <= 0.015 mg/L)"
    }
}

class WaterQualityAlertSystem:
    def __init__(self, thresholds: Optional[Dict[str, Dict[str, Any]]] = None):
        self.thresholds = thresholds if thresholds else STANDARD_THRESHOLDS.copy()
        self.sensor_records: List[Dict[str, Any]] = []
        self.alerts: List[Dict[str, Any]] = []
        self.error_logs: List[str] = []

    def update_threshold(self, metric: str, min_val: Optional[float], max_val: Optional[float]):
        """Dynamically update safety thresholds."""
        if metric in self.thresholds:
            if min_val is not None:
                self.thresholds[metric]["min"] = float(min_val)
            if max_val is not None:
                self.thresholds[metric]["max"] = float(max_val)

    def validate_reading(self, raw_row: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Validate and type-cast a single sensor reading row, handling errors gracefully."""
        try:
            station_id = str(raw_row.get("station_id", "")).strip()
            if not station_id:
                return None, "Missing station_id"

            timestamp_str = str(raw_row.get("timestamp", "")).strip()
            if not timestamp_str:
                timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            clean_row = {
                "station_id": station_id,
                "timestamp": timestamp_str
            }

            for metric in self.thresholds.keys():
                val_raw = raw_row.get(metric)
                if val_raw is None or str(val_raw).strip() == "":
                    clean_row[metric] = None
                    continue

                try:
                    val = float(val_raw)
                    # Physical sanity checks
                    if metric == "ph" and not (0 <= val <= 14):
                        return None, f"Out of physical bounds for pH: {val}"
                    if metric in ["turbidity", "chlorine", "dissolved_oxygen", "lead"] and val < 0:
                        return None, f"Negative value for {metric}: {val}"
                    clean_row[metric] = val
                except (ValueError, TypeError):
                    return None, f"Invalid numeric format for {metric}: '{val_raw}'"

            return clean_row, None
        except Exception as e:
            return None, f"Unexpected error parsing row: {str(e)}"

    def evaluate_alert(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate a validated record against current thresholds to detect unsafe conditions."""
        station_alerts = []
        station_id = record["station_id"]
        timestamp = record["timestamp"]

        for metric, bounds in self.thresholds.items():
            val = record.get(metric)
            if val is None:
                continue

            min_b = bounds.get("min")
            max_b = bounds.get("max")
            unit = bounds.get("unit", "")

            severity = None
            msg = None

            if min_b is not None and val < min_b:
                diff = min_b - val
                # Critical if deviation is greater than 25% of lower threshold or extreme
                severity = "CRITICAL" if (diff / max(abs(min_b), 1e-4) > 0.25) else "WARNING"
                msg = f"{metric.upper()} level is dangerously LOW: {val:.3f} {unit} (Min safe: {min_b} {unit})"
            elif max_b is not None and val > max_b:
                diff = val - max_b
                severity = "CRITICAL" if (diff / max(abs(max_b), 1e-4) > 0.3) else "WARNING"
                msg = f"{metric.upper()} level EXCEEDS safe limit: {val:.3f} {unit} (Max safe: {max_b} {unit})"

            if severity and msg:
                alert_entry = {
                    "station_id": station_id,
                    "timestamp": timestamp,
                    "metric": metric,
                    "value": val,
                    "safe_range": f"{min_b} - {max_b} {unit}",
                    "severity": severity,
                    "message": msg
                }
                station_alerts.append(alert_entry)

        return station_alerts

    def process_record(self, raw_row: Dict[str, Any]) -> Tuple[bool, Optional[str], List[Dict[str, Any]]]:
        """Process a single record, log alerts, and add to database records."""
        clean_row, err = self.validate_reading(raw_row)
        if err:
            self.error_logs.append(f"Validation Error [{raw_row.get('station_id', 'UNKNOWN')}]: {err}")
            return False, err, []

        self.sensor_records.append(clean_row)
        new_alerts = self.evaluate_alert(clean_row)
        self.alerts.extend(new_alerts)
        return True, None, new_alerts

    def load_from_csv(self, filepath: str) -> Dict[str, int]:
        """Read sensor data from a CSV file, handling malformed lines gracefully."""
        stats = {"total": 0, "valid": 0, "errors": 0, "alerts_detected": 0}
        if not os.path.exists(filepath):
            self.error_logs.append(f"File not found: {filepath}")
            return stats

        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats["total"] += 1
                success, err, detected_alerts = self.process_record(row)
                if success:
                    stats["valid"] += 1
                    stats["alerts_detected"] += len(detected_alerts)
                else:
                    stats["errors"] += 1

        return stats

    def export_summary_report(self, filepath: str) -> bool:
        """Produce a comprehensive executive summary report (text/markdown format)."""
        try:
            summary = self.generate_summary_metrics()
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# MUNICIPAL WATER QUALITY ALERT SYSTEM - SUMMARY REPORT\n")
                f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"## System Executive Overview\n")
                f.write(f"- Total Valid Records Processed: {summary['total_records']}\n")
                f.write(f"- Active Monitoring Stations: {len(summary['stations'])}\n")
                f.write(f"- Total Alerts Triggered: {len(self.alerts)}\n")
                f.write(f"  - Critical Alerts: {summary['critical_alerts_count']}\n")
                f.write(f"  - Warning Alerts: {summary['warning_alerts_count']}\n")
                f.write(f"- Data Acquisition Errors Logged: {len(self.error_logs)}\n\n")

                f.write(f"## Metric Statistics Across All Stations\n")
                f.write(f"| Metric | Mean | Min | Max | Safe Thresholds |\n")
                f.write(f"|---|---|---|---|---|\n")
                for metric, stats in summary["metric_stats"].items():
                    unit = self.thresholds.get(metric, {}).get("unit", "")
                    min_t = self.thresholds.get(metric, {}).get("min", "-")
                    max_t = self.thresholds.get(metric, {}).get("max", "-")
                    f.write(f"| {metric.capitalize()} | {stats['mean']:.2f} {unit} | {stats['min']:.2f} {unit} | {stats['max']:.2f} {unit} | {min_t} - {max_t} {unit} |\n")

                f.write(f"\n## Recent Triggered Alerts\n")
                if not self.alerts:
                    f.write("All monitored stations are within normal compliance limits. No alerts.\n")
                else:
                    f.write(f"| Time | Station | Severity | Metric | Value | Alert Description |\n")
                    f.write(f"|---|---|---|---|---|---|\n")
                    for a in self.alerts[-30:]:
                        f.write(f"| {a['timestamp']} | {a['station_id']} | {a['severity']} | {a['metric']} | {a['value']:.3f} | {a['message']} |\n")

                f.write(f"\n## System Error & Anomaly Log\n")
                if not self.error_logs:
                    f.write("Zero data parsing errors recorded.\n")
                else:
                    for err in self.error_logs[-20:]:
                        f.write(f"- {err}\n")

            return True
        except Exception as e:
            self.error_logs.append(f"Failed to export report: {str(e)}")
            return False

    def generate_summary_metrics(self) -> Dict[str, Any]:
        """Compute key summary metrics (mean, min, max, alert breakdown)."""
        stations = set()
        metric_values: Dict[str, List[float]] = {k: [] for k in self.thresholds.keys()}

        for rec in self.sensor_records:
            stations.add(rec["station_id"])
            for m in self.thresholds.keys():
                val = rec.get(m)
                if val is not None:
                    metric_values[m].append(val)

        stats = {}
        for m, vals in metric_values.items():
            if vals:
                stats[m] = {
                    "count": len(vals),
                    "mean": sum(vals) / len(vals),
                    "min": min(vals),
                    "max": max(vals)
                }
            else:
                stats[m] = {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0}

        crit_count = sum(1 for a in self.alerts if a["severity"] == "CRITICAL")
        warn_count = sum(1 for a in self.alerts if a["severity"] == "WARNING")

        return {
            "total_records": len(self.sensor_records),
            "stations": list(sorted(stations)),
            "metric_stats": stats,
            "critical_alerts_count": crit_count,
            "warning_alerts_count": warn_count
        }

    def simulate_telemetry_step(self, station_ids: Optional[List[str]] = None, contamination_prob: float = 0.12) -> List[Dict[str, Any]]:
        """Simulate a real-time telemetric stream cycle from stations with optional disturbance."""
        if not station_ids:
            station_ids = ["STATION-ALPHA-01", "STATION-BETA-02", "STATION-GAMMA-03", "STATION-DELTA-04"]

        new_events = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for sid in station_ids:
            has_spike = (random.random() < contamination_prob)
            
            # Base healthy water parameters
            ph = random.gauss(7.4, 0.25)
            turbidity = random.uniform(0.3, 1.8)
            chlorine = random.gauss(1.8, 0.3)
            temperature = random.gauss(18.5, 1.2)
            dissolved_oxygen = random.gauss(8.8, 0.4)
            lead = max(0.0, random.gauss(0.003, 0.001))

            if has_spike:
                anomaly_type = random.choice(["acid_spill", "pipe_corrosion_lead", "turbidity_runoff", "chlorine_depletion"])
                if anomaly_type == "acid_spill":
                    ph = random.uniform(4.5, 5.8)
                elif anomaly_type == "pipe_corrosion_lead":
                    lead = random.uniform(0.018, 0.045)
                    turbidity = random.uniform(4.0, 7.5)
                elif anomaly_type == "turbidity_runoff":
                    turbidity = random.uniform(6.5, 14.0)
                elif anomaly_type == "chlorine_depletion":
                    chlorine = random.uniform(0.01, 0.12)

            raw_row = {
                "station_id": sid,
                "timestamp": now,
                "ph": round(ph, 2),
                "turbidity": round(turbidity, 2),
                "chlorine": round(chlorine, 2),
                "temperature": round(temperature, 1),
                "dissolved_oxygen": round(dissolved_oxygen, 2),
                "lead": round(lead, 4)
            }

            _, _, alerts = self.process_record(raw_row)
            new_events.append({
                "record": raw_row,
                "alerts": alerts
            })

        return new_events

    def clear_data(self):
        """Reset records, alerts, and error logs."""
        self.sensor_records.clear()
        self.alerts.clear()
        self.error_logs.clear()
