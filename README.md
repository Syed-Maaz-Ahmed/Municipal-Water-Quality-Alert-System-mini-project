# Municipal Water Quality Alert System

A modular, enterprise-grade Python application built for municipal environmental water quality monitoring, anomaly detection, real-time simulation, and compliance reporting.

---

## 🌟 Key Features

1. **Modular Architecture**:
   - `water_quality_core.py`: Pure computational & analytics engine covering threshold evaluation, anomaly classification (Warning vs. Critical), statistical summary metrics, real-time telemetry streaming simulation, and error-tolerant CSV parsing.
   - `app_gui.py`: Modern, high-definition graphical interface built with `CustomTkinter` and `Matplotlib` embedded plots.
   - `generate_sample_data.py`: Telemetry generator that creates realistic environmental data with intentional contaminant spikes and data formatting anomalies.
   - `test_water_quality.py`: Automated `unittest` suite validating safety bounds, error resilience, and alert accuracy.

2. **Water Quality Safety Parameters Monitored (EPA/WHO Standards)**:
   - **pH**: Acidity & basicity limits (6.5 - 8.5)
   - **Turbidity**: Cloudiness & suspended particulates (safe ≤ 5.0 NTU)
   - **Chlorine**: Residual disinfectant levels (safe 0.2 - 4.0 mg/L)
   - **Dissolved Oxygen**: Aerobic balance (safe ≥ 6.0 mg/L)
   - **Lead Contamination**: Action limit (safe ≤ 0.015 mg/L)
   - **Water Temperature**: Safe range (4.0 - 25.0 °C)

3. **Interactive GUI Capabilities**:
   - **Live Metric Plotting**: Embedded dark-themed matplotlib chart showing telemetry history and highlighted safe operating bands.
   - **Live Sensor Telemetry Simulation**: Background multi-threaded simulator streaming real-time station data.
   - **Alert Center**: Displays timestamped critical and warning alert logs with safe limits and descriptions.
   - **Configurable Thresholds**: GUI modal dialog to dynamically update municipal thresholds on the fly.
   - **Report Export**: Exports clean executive summary markdown/text reports with mean/min/max statistics.
   - **Data Error Logs**: Tracks corrupted sensor readings and out-of-physical-bound inputs gracefully.

---

## 🚀 How to Run

### 1. Launch the Modern Web Application (Recommended)
```powershell
python web_app.py
```
Then visit **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your web browser.

### 2. Launch the Desktop GUI
```powershell
python app_gui.py
```

### 3. Run the Automated Test Suite
```powershell
python test_water_quality.py
```

### 4. Generate New Sample Sensor Data
```powershell
python generate_sample_data.py
```
