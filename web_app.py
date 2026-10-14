import os
import io
import csv
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename

from water_quality_core import WaterQualityAlertSystem, STANDARD_THRESHOLDS

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB upload limit

# Global system instance
system = WaterQualityAlertSystem()

# Auto-load initial sample dataset if present
if os.path.exists("sensor_telemetry_sample.csv"):
    system.load_from_csv("sensor_telemetry_sample.csv")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/summary", methods=["GET"])
def get_summary():
    """Return dashboard summary stats and recent telemetry."""
    summary = system.generate_summary_metrics()
    
    # Return last 60 records for charting & table
    recent_records = system.sensor_records[-60:]
    recent_alerts = system.alerts[-40:]
    recent_errors = system.error_logs[-30:]

    return jsonify({
        "status": "success",
        "summary": summary,
        "thresholds": system.thresholds,
        "recent_records": recent_records,
        "recent_alerts": list(reversed(recent_alerts)),
        "recent_errors": list(reversed(recent_errors))
    })

@app.route("/api/simulate-step", methods=["POST"])
def simulate_step():
    """Trigger a live telemetry cycle with randomized anomaly probability."""
    data = request.get_json(silent=True) or {}
    prob = float(data.get("contamination_prob", 0.15))
    events = system.simulate_telemetry_step(contamination_prob=prob)
    return jsonify({
        "status": "success",
        "events_count": len(events),
        "new_events": events,
        "summary": system.generate_summary_metrics()
    })

@app.route("/api/upload-csv", methods=["POST"])
def upload_csv():
    """Handle CSV file upload and parse records."""
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "No file selected"}), 400

    if not file.filename.lower().endswith(".csv"):
        return jsonify({"status": "error", "message": "Only CSV files are supported"}), 400

    try:
        stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
        reader = csv.DictReader(stream)
        stats = {"total": 0, "valid": 0, "errors": 0, "alerts_detected": 0}

        for row in reader:
            stats["total"] += 1
            success, err, detected_alerts = system.process_record(row)
            if success:
                stats["valid"] += 1
                stats["alerts_detected"] += len(detected_alerts)
            else:
                stats["errors"] += 1

        return jsonify({
            "status": "success",
            "stats": stats,
            "message": f"Processed {stats['total']} records ({stats['valid']} valid, {stats['errors']} invalid, {stats['alerts_detected']} alerts)."
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to parse CSV: {str(e)}"}), 500

@app.route("/api/thresholds", methods=["GET", "POST"])
def manage_thresholds():
    """Get or update safety threshold configurations."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        for metric, bounds in data.items():
            if metric in system.thresholds:
                min_v = bounds.get("min")
                max_v = bounds.get("max")
                system.update_threshold(
                    metric, 
                    float(min_v) if min_v is not None and min_v != "" else None,
                    float(max_v) if max_v is not None and max_v != "" else None
                )
        return jsonify({"status": "success", "thresholds": system.thresholds})
    
    return jsonify({"status": "success", "thresholds": system.thresholds})

@app.route("/api/export-report", methods=["GET"])
def export_report():
    """Generate and download the executive compliance report."""
    filename = f"water_quality_incident_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    temp_path = os.path.join("static", filename)
    
    success = system.export_summary_report(temp_path)
    if not success or not os.path.exists(temp_path):
        return jsonify({"status": "error", "message": "Failed to create report"}), 500

    return send_file(temp_path, as_attachment=True, download_name=filename)

@app.route("/api/clear-data", methods=["POST"])
def clear_data():
    """Reset telemetry records and alerts."""
    system.clear_data()
    return jsonify({"status": "success", "message": "System data and alerts cleared."})

if __name__ == "__main__":
    print("Starting AquaGuard Municipal Web Server on http://localhost:5000 ...")
    app.run(host="127.0.0.1", port=5000, debug=False)
