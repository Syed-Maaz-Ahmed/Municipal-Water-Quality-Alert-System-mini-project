let activeMetric = "ph";
let simulationInterval = null;
let telemetryChart = null;
let cachedThresholds = {};

// Initialize application on page load
document.addEventListener("DOMContentLoaded", () => {
  initChart();
  fetchDashboardData();
  
  // Periodic poll to refresh telemetry every 5 seconds if idle
  setInterval(() => {
    if (!simulationInterval) {
      fetchDashboardData(true);
    }
  }, 5000);
});

function initChart() {
  const ctx = document.getElementById("telemetryChart").getContext("2d");
  
  telemetryChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Measured Sensor Value",
          data: [],
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56, 189, 248, 0.15)",
          borderWidth: 2.5,
          tension: 0.3,
          pointRadius: 4,
          pointBackgroundColor: "#0284c7",
          fill: false
        },
        {
          label: "Min Safe Limit",
          data: [],
          borderColor: "#ef4444",
          borderWidth: 1.5,
          borderDash: [5, 5],
          pointRadius: 0,
          fill: false
        },
        {
          label: "Max Safe Limit",
          data: [],
          borderColor: "#f43f5e",
          borderWidth: 1.5,
          borderDash: [5, 5],
          pointRadius: 0,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false
      },
      plugins: {
        legend: {
          labels: {
            color: "#cbd5e1",
            font: { family: "Outfit", size: 12 }
          }
        },
        tooltip: {
          backgroundColor: "rgba(15, 23, 42, 0.9)",
          titleColor: "#38bdf8",
          bodyColor: "#f8fafc",
          borderColor: "rgba(255, 255, 255, 0.1)",
          borderWidth: 1,
          padding: 10
        }
      },
      scales: {
        x: {
          ticks: { color: "#64748b", maxRotation: 45, minRotation: 0, font: { family: "Outfit", size: 10 } },
          grid: { color: "rgba(255, 255, 255, 0.05)" }
        },
        y: {
          ticks: { color: "#94a3b8", font: { family: "Outfit", size: 11 } },
          grid: { color: "rgba(255, 255, 255, 0.05)" }
        }
      }
    }
  });
}

async function fetchDashboardData(silent = false) {
  try {
    const res = await fetch("/api/summary");
    if (!res.ok) throw new Error("Network error fetching summary");
    const data = await res.json();

    cachedThresholds = data.thresholds;
    updateKPIs(data.summary);
    renderThresholdsList(data.thresholds);
    renderAlertsTable(data.recent_alerts);
    renderErrorLogs(data.recent_errors);
    updateChartData(data.recent_records);
  } catch (err) {
    if (!silent) console.error("Error refreshing dashboard:", err);
  }
}

function updateKPIs(summary) {
  document.getElementById("kpiTotalRecords").innerText = summary.total_records.toLocaleString();
  document.getElementById("kpiStationsCount").innerText = summary.stations.length;
  document.getElementById("kpiCriticalAlerts").innerText = summary.critical_alerts_count;
  document.getElementById("kpiWarningAlerts").innerText = summary.warning_alerts_count;
}

function selectMetric(metric) {
  activeMetric = metric;
  document.querySelectorAll(".metric-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.metric === metric);
  });
  fetchDashboardData();
}

function updateChartData(records) {
  if (!telemetryChart || !records) return;

  const labels = [];
  const vals = [];
  const minLines = [];
  const maxLines = [];

  const threshold = cachedThresholds[activeMetric] || {};
  const minVal = threshold.min !== undefined ? threshold.min : null;
  const maxVal = threshold.max !== undefined ? threshold.max : null;

  records.forEach(rec => {
    const v = rec[activeMetric];
    if (v !== undefined && v !== null) {
      const timeOnly = rec.timestamp ? rec.timestamp.split(" ")[1] || rec.timestamp : "";
      labels.push(`${rec.station_id.split("-").pop()} (${timeOnly})`);
      vals.push(v);
      minLines.push(minVal);
      maxLines.push(maxVal);
    }
  });

  telemetryChart.data.labels = labels;
  telemetryChart.data.datasets[0].label = `${activeMetric.toUpperCase()} (${threshold.unit || ""})`;
  telemetryChart.data.datasets[0].data = vals;
  telemetryChart.data.datasets[1].data = minLines;
  telemetryChart.data.datasets[2].data = maxLines;

  telemetryChart.update();
}

function renderThresholdsList(thresholds) {
  const container = document.getElementById("thresholdDisplayList");
  container.innerHTML = "";

  for (const [key, data] of Object.entries(thresholds)) {
    const item = document.createElement("div");
    item.className = "threshold-item";
    const minText = data.min !== null && data.min !== undefined ? data.min : "-";
    const maxText = data.max !== null && data.max !== undefined ? data.max : "-";

    item.innerHTML = `
      <div class="threshold-info">
        <span class="threshold-name">${key.replace("_", " ")}</span>
        <span class="threshold-desc">${data.description}</span>
      </div>
      <span class="threshold-badge">${minText} - ${maxText} ${data.unit}</span>
    `;
    container.appendChild(item);
  }
}

function renderAlertsTable(alerts) {
  const tbody = document.getElementById("alertsTableBody");
  if (!alerts || alerts.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 2rem; color: #64748b;">
          All water parameters are within standard EPA safe limits. No active alerts.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = alerts.map(a => {
    const badgeClass = a.severity === "CRITICAL" ? "badge-crit" : "badge-warn";
    const valFormatted = typeof a.value === "number" ? a.value.toFixed(3) : a.value;

    return `
      <tr>
        <td style="white-space: nowrap; font-size: 0.8rem;">${a.timestamp}</td>
        <td><strong style="color: #cbd5e1;">${a.station_id}</strong></td>
        <td><span class="${badgeClass}">${a.severity}</span></td>
        <td><span style="color: #38bdf8; font-weight: 600;">${a.metric.toUpperCase()}</span></td>
        <td><strong>${valFormatted}</strong></td>
        <td style="color: #94a3b8; font-size: 0.8rem;">${a.safe_range}</td>
        <td style="color: ${a.severity === 'CRITICAL' ? '#fca5a5' : '#fde047'}">${a.message}</td>
      </tr>
    `;
  }).join("");
}

function renderErrorLogs(errors) {
  const consoleBox = document.getElementById("errorConsole");
  if (!errors || errors.length === 0) {
    consoleBox.innerHTML = `<div>[${new Date().toLocaleTimeString()}] Telemetry bus online. Zero parsing errors detected.</div>`;
    return;
  }

  consoleBox.innerHTML = errors.map(e => `
    <div class="error-log-entry">⚠ ${e}</div>
  `).join("");
}

// Live Streaming Simulation Toggle
function toggleSimulation() {
  const btn = document.getElementById("btnToggleSim");
  const label = document.getElementById("simBtnLabel");
  const statusText = document.getElementById("systemStatusText");

  if (!simulationInterval) {
    // Start simulation loop
    btn.classList.add("active-sim");
    label.innerText = "Stop Live Stream";
    statusText.innerText = "Live Telemetry Streaming";

    // Immediate first tick
    simulateStep();
    simulationInterval = setInterval(simulateStep, 2500);
  } else {
    // Stop simulation loop
    clearInterval(simulationInterval);
    simulationInterval = null;
    btn.classList.remove("active-sim");
    label.innerText = "Start Live Stream";
    statusText.innerText = "Telemetry Online";
  }
}

async function simulateStep() {
  try {
    const res = await fetch("/api/simulate-step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contamination_prob: 0.20 })
    });
    if (res.ok) {
      await fetchDashboardData(true);
    }
  } catch (e) {
    console.error("Simulation error:", e);
  }
}

// CSV Telemetry File Upload
async function handleCsvUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload-csv", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (res.ok) {
      alert(`CSV Ingestion Completed!\n\n${data.message}`);
      fetchDashboardData();
    } else {
      alert(`Upload error: ${data.message}`);
    }
  } catch (err) {
    alert("Network error processing CSV file.");
  }
  event.target.value = "";
}

// Export Summary Report
function downloadReport() {
  window.location.href = "/api/export-report";
}

// Clear Telemetry Data
async function clearTelemetry() {
  if (confirm("Are you sure you want to clear all telemetry records and active alert flags?")) {
    await fetch("/api/clear-data", { method: "POST" });
    fetchDashboardData();
  }
}

// Modals: Threshold Management
function openThresholdModal() {
  const container = document.getElementById("modalThresholdFields");
  container.innerHTML = "";

  for (const [metric, bounds] of Object.entries(cachedThresholds)) {
    const group = document.createElement("div");
    group.className = "form-group-grid";
    group.innerHTML = `
      <div class="form-field">
        <label>${metric.toUpperCase()} (${bounds.unit}) Min Safe</label>
        <input type="number" step="any" id="thresh_min_${metric}" value="${bounds.min !== null && bounds.min !== undefined ? bounds.min : ''}">
      </div>
      <div class="form-field">
        <label>${metric.toUpperCase()} (${bounds.unit}) Max Safe</label>
        <input type="number" step="any" id="thresh_max_${metric}" value="${bounds.max !== null && bounds.max !== undefined ? bounds.max : ''}">
      </div>
    `;
    container.appendChild(group);
  }

  document.getElementById("thresholdModal").classList.add("open");
}

function closeThresholdModal() {
  document.getElementById("thresholdModal").classList.remove("open");
}

async function saveThresholds(e) {
  e.preventDefault();
  const payload = {};

  for (const metric of Object.keys(cachedThresholds)) {
    const minVal = document.getElementById(`thresh_min_${metric}`).value;
    const maxVal = document.getElementById(`thresh_max_${metric}`).value;
    payload[metric] = {
      min: minVal !== "" ? parseFloat(minVal) : null,
      max: maxVal !== "" ? parseFloat(maxVal) : null
    };
  }

  try {
    const res = await fetch("/api/thresholds", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      closeThresholdModal();
      fetchDashboardData();
    } else {
      alert("Failed to update thresholds.");
    }
  } catch (err) {
    alert("Error communicating with server.");
  }
}
