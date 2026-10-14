import csv
import random
from datetime import datetime, timedelta

def generate_sample_data(filename="sensor_telemetry_sample.csv", count=150):
    stations = ["STATION-ALPHA-01", "STATION-BETA-02", "STATION-GAMMA-03", "STATION-DELTA-04"]
    fieldnames = ["station_id", "timestamp", "ph", "turbidity", "chlorine", "temperature", "dissolved_oxygen", "lead"]

    start_time = datetime.now() - timedelta(hours=6)
    rows = []

    for i in range(count):
        station = random.choice(stations)
        t = start_time + timedelta(minutes=i * 2.5)
        
        # Inject deliberate anomalies and noise
        r = random.random()
        if r < 0.05:
            # Acidic runoff
            ph = round(random.uniform(5.0, 6.2), 2)
            turb = round(random.uniform(1.0, 3.5), 2)
            ch = round(random.uniform(1.2, 2.0), 2)
            temp = round(random.uniform(17.0, 22.0), 1)
            do = round(random.uniform(7.0, 8.5), 2)
            pb = round(random.uniform(0.002, 0.005), 4)
        elif r < 0.10:
            # Sediment & storm turbidity spike
            ph = round(random.uniform(7.0, 7.8), 2)
            turb = round(random.uniform(6.0, 16.5), 2)
            ch = round(random.uniform(0.5, 1.4), 2)
            temp = round(random.uniform(18.0, 23.0), 1)
            do = round(random.uniform(6.5, 8.0), 2)
            pb = round(random.uniform(0.003, 0.010), 4)
        elif r < 0.15:
            # Disinfection failure (low chlorine) or lead contamination
            ph = round(random.uniform(7.2, 8.0), 2)
            turb = round(random.uniform(0.5, 2.0), 2)
            ch = round(random.uniform(0.02, 0.15), 2)
            temp = round(random.uniform(19.0, 24.0), 1)
            do = round(random.uniform(7.5, 9.0), 2)
            pb = round(random.uniform(0.018, 0.035), 4)
        elif r < 0.18:
            # Bad sensor read / Malformed data test case
            ph = "N/A"
            turb = round(random.uniform(0.5, 2.0), 2)
            ch = round(random.uniform(1.0, 2.5), 2)
            temp = -999.0  # Erroneous
            do = "CORRUPT"
            pb = 0.001
        else:
            # Normal clean water
            ph = round(random.gauss(7.35, 0.25), 2)
            turb = round(random.uniform(0.3, 1.8), 2)
            ch = round(random.gauss(1.9, 0.35), 2)
            temp = round(random.gauss(18.0, 1.5), 1)
            do = round(random.gauss(8.6, 0.4), 2)
            pb = round(max(0.0, random.gauss(0.0025, 0.0008)), 4)

        rows.append({
            "station_id": station,
            "timestamp": t.strftime("%Y-%m-%d %H:%M:%S"),
            "ph": ph,
            "turbidity": turb,
            "chlorine": ch,
            "temperature": temp,
            "dissolved_oxygen": do,
            "lead": pb
        })

    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Sample dataset generated successfully: {filename} ({len(rows)} records)")

if __name__ == "__main__":
    generate_sample_data()
