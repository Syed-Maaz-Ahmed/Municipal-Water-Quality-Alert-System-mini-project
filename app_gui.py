import os
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk

# Matplotlib integration into Tkinter
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from water_quality_core import WaterQualityAlertSystem, STANDARD_THRESHOLDS

# Set Theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class MunicipalWaterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("EcoPure - Municipal Water Quality Alert & Telemetry System")
        self.geometry("1300x820")
        self.minsize(1100, 720)

        # Core logic system
        self.system = WaterQualityAlertSystem()
        self.simulation_running = False
        self.sim_thread = None

        # Layout configure
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_main_view()

        # Load initial sample data if exists
        if os.path.exists("sensor_telemetry_sample.csv"):
            self.system.load_from_csv("sensor_telemetry_sample.csv")
            self.refresh_dashboard()

    def _build_sidebar(self):
        """Construct the sidebar for actions and controls."""
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)

        # Logo and Title
        title_label = ctk.CTkLabel(
            self.sidebar, 
            text="💧 AquaGuard\nMunicipal Ops", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#38bdf8"
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 15))

        subtitle = ctk.CTkLabel(
            self.sidebar,
            text="Environmental Tech Startup",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="#94a3b8"
        )
        subtitle.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Action Buttons
        self.btn_load_csv = ctk.CTkButton(
            self.sidebar, text="📂 Ingest Sensor CSV",
            fg_color="#0284c7", hover_color="#0369a1",
            command=self.load_csv_dialog
        )
        self.btn_load_csv.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.btn_sim_toggle = ctk.CTkButton(
            self.sidebar, text="▶ Start Live Simulation",
            fg_color="#10b981", hover_color="#059669",
            command=self.toggle_simulation
        )
        self.btn_sim_toggle.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        self.btn_export = ctk.CTkButton(
            self.sidebar, text="📑 Export Incident Report",
            fg_color="#6366f1", hover_color="#4f46e5",
            command=self.export_report_dialog
        )
        self.btn_export.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        self.btn_thresholds = ctk.CTkButton(
            self.sidebar, text="⚙ Edit Thresholds",
            fg_color="#334155", hover_color="#475569",
            command=self.open_threshold_dialog
        )
        self.btn_thresholds.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

        self.btn_clear = ctk.CTkButton(
            self.sidebar, text="🗑 Clear Telemetry Data",
            fg_color="#e11d48", hover_color="#be123c",
            command=self.clear_all_data
        )
        self.btn_clear.grid(row=6, column=0, padx=20, pady=10, sticky="ew")

        # Status badge in sidebar
        self.status_frame = ctk.CTkFrame(self.sidebar, fg_color="#1e293b", corner_radius=8)
        self.status_frame.grid(row=11, column=0, padx=15, pady=20, sticky="ew")
        
        self.lbl_status = ctk.CTkLabel(
            self.status_frame,
            text="● System Online",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#10b981"
        )
        self.lbl_status.pack(pady=8)

    def _build_main_view(self):
        """Construct the tabs and main dashboard displays."""
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=0, column=1, padx=20, pady=15, sticky="nsew")

        self.tab_dash = self.tabview.add("📊 Dashboard & Telemetry")
        self.tab_alerts = self.tabview.add("🚨 Active Alerts")
        self.tab_logs = self.tabview.add("🛠 Data & Error Logs")

        self._setup_dashboard_tab()
        self._setup_alerts_tab()
        self._setup_logs_tab()

    def _setup_dashboard_tab(self):
        # KPI Cards Frame
        kpi_frame = ctk.CTkFrame(self.tab_dash, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=10, pady=5)
        kpi_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.card_records = self._create_kpi_card(kpi_frame, 0, "Total Ingested Reads", "0", "#38bdf8")
        self.card_stations = self._create_kpi_card(kpi_frame, 1, "Active Stations", "0", "#a78bfa")
        self.card_crit = self._create_kpi_card(kpi_frame, 2, "Critical Alerts", "0", "#ef4444")
        self.card_warn = self._create_kpi_card(kpi_frame, 3, "Warning Flags", "0", "#f59e0b")

        # Metric Plots Frame
        plot_controls = ctk.CTkFrame(self.tab_dash, fg_color="transparent")
        plot_controls.pack(fill="x", padx=10, pady=(10, 5))

        lbl_metric = ctk.CTkLabel(plot_controls, text="Select Metric to Inspect:", font=ctk.CTkFont(weight="bold"))
        lbl_metric.pack(side="left", padx=5)

        self.metric_combo = ctk.CTkComboBox(
            plot_controls,
            values=["ph", "turbidity", "chlorine", "dissolved_oxygen", "lead", "temperature"],
            command=self.update_plot
        )
        self.metric_combo.set("ph")
        self.metric_combo.pack(side="left", padx=10)

        # Matplotlib Canvas Frame
        self.chart_frame = ctk.CTkFrame(self.tab_dash, fg_color="#18181b", corner_radius=8)
        self.chart_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.fig = Figure(figsize=(7, 3.8), dpi=100, facecolor="#18181b")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#27272a")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def _create_kpi_card(self, parent, col, title, initial_val, text_color):
        card = ctk.CTkFrame(parent, fg_color="#1e293b", corner_radius=8, height=80)
        card.grid(row=0, column=col, padx=6, pady=5, sticky="ew")

        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12), text_color="#94a3b8")
        lbl_title.pack(pady=(10, 0))

        lbl_val = ctk.CTkLabel(card, text=initial_val, font=ctk.CTkFont(size=22, weight="bold"), text_color=text_color)
        lbl_val.pack(pady=(2, 10))
        return lbl_val

    def _setup_alerts_tab(self):
        # Alerts Table
        container = ctk.CTkFrame(self.tab_alerts)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Style standard ttk Treeview to match dark theme
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Alerts.Treeview",
                        background="#1e293b",
                        foreground="#f8fafc",
                        rowheight=28,
                        fieldbackground="#1e293b",
                        bordercolor="#334155")
        style.configure("Alerts.Treeview.Heading",
                        background="#0f172a",
                        foreground="#38bdf8",
                        font=("Segoe UI", 10, "bold"))
        style.map("Alerts.Treeview", background=[('selected', '#0284c7')])

        columns = ("Timestamp", "Station", "Severity", "Metric", "Value", "Safe Limit", "Description")
        self.tree_alerts = ttk.Treeview(container, columns=columns, show="headings", style="Alerts.Treeview")

        for col in columns:
            self.tree_alerts.heading(col, text=col)
            if col in ["Timestamp", "Description"]:
                self.tree_alerts.column(col, width=190 if col == "Timestamp" else 300)
            else:
                self.tree_alerts.column(col, width=100, anchor="center")

        scroll_y = ttk.Scrollbar(container, orient="vertical", command=self.tree_alerts.yview)
        self.tree_alerts.configure(yscrollcommand=scroll_y.set)

        self.tree_alerts.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

    def _setup_logs_tab(self):
        container = ctk.CTkFrame(self.tab_logs)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        lbl = ctk.CTkLabel(container, text="System Error & Ingestion Anomaly Logs", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(anchor="w", padx=10, pady=(5, 5))

        self.log_textbox = ctk.CTkTextbox(container, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=10)

    def refresh_dashboard(self):
        summary = self.system.generate_summary_metrics()
        self.card_records.configure(text=str(summary["total_records"]))
        self.card_stations.configure(text=str(len(summary["stations"])))
        self.card_crit.configure(text=str(summary["critical_alerts_count"]))
        self.card_warn.configure(text=str(summary["warning_alerts_count"]))

        # Populate Alerts
        for item in self.tree_alerts.get_children():
            self.tree_alerts.delete(item)

        for a in reversed(self.system.alerts[-150:]):
            val_str = f"{a['value']:.3f}" if isinstance(a['value'], float) else str(a['value'])
            self.tree_alerts.insert("", "end", values=(
                a["timestamp"], a["station_id"], a["severity"], a["metric"].upper(),
                val_str, a["safe_range"], a["message"]
            ))

        # Populate Logs
        self.log_textbox.delete("0.0", "end")
        if not self.system.error_logs:
            self.log_textbox.insert("end", "[INFO] No data validation errors or sensor communication faults logged.\n")
        else:
            for l in reversed(self.system.error_logs[-100:]):
                self.log_textbox.insert("end", f"{l}\n")

        self.update_plot()

    def update_plot(self, *args):
        metric = self.metric_combo.get()
        self.ax.clear()

        # Thresholds
        bounds = self.system.thresholds.get(metric, {})
        min_b = bounds.get("min")
        max_b = bounds.get("max")
        unit = bounds.get("unit", "")

        # Extract readings for the metric
        points = []
        for r in self.system.sensor_records[-80:]:
            val = r.get(metric)
            if val is not None:
                points.append((r["timestamp"], val, r["station_id"]))

        if points:
            x_vals = range(len(points))
            y_vals = [p[1] for p in points]

            self.ax.plot(x_vals, y_vals, marker="o", markersize=3, color="#38bdf8", label=f"Readings ({metric})", linewidth=1.5)

            # Draw threshold lines
            if min_b is not None:
                self.ax.axhline(min_b, color="#ef4444", linestyle="--", linewidth=1.2, label=f"Min Safe ({min_b} {unit})")
            if max_b is not None:
                self.ax.axhline(max_b, color="#ef4444", linestyle="--", linewidth=1.2, label=f"Max Safe ({max_b} {unit})")

            # Fill safe zone
            if min_b is not None and max_b is not None:
                self.ax.axhspan(min_b, max_b, color="#10b981", alpha=0.1, label="Safe Operating Range")

        self.ax.set_title(f"Telemetry History: {metric.upper()} ({unit})", color="#f8fafc", fontsize=11, fontweight="bold")
        self.ax.set_ylabel(unit, color="#94a3b8")
        self.ax.tick_params(colors="#94a3b8", labelsize=9)
        self.ax.grid(True, linestyle=":", alpha=0.4, color="#52525b")

        handles, labels = self.ax.get_legend_handles_labels()
        if handles:
            self.ax.legend(loc="upper right", facecolor="#18181b", edgecolor="#3f3f46", labelcolor="#e4e4e7", fontsize=8)

        self.canvas.draw_idle()

    def load_csv_dialog(self):
        filepath = filedialog.askopenfilename(
            title="Select Sensor Telemetry CSV File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if filepath:
            stats = self.system.load_from_csv(filepath)
            self.refresh_dashboard()
            messagebox.showinfo(
                "Ingestion Complete",
                f"Successfully read sensor telemetry.\n\n"
                f"Total Records: {stats['total']}\n"
                f"Valid Records: {stats['valid']}\n"
                f"Errors Encountered: {stats['errors']}\n"
                f"Alerts Triggered: {stats['alerts_detected']}"
            )

    def toggle_simulation(self):
        if not self.simulation_running:
            self.simulation_running = True
            self.btn_sim_toggle.configure(text="⏹ Stop Simulation", fg_color="#ef4444", hover_color="#dc2626")
            self.lbl_status.configure(text="● Simulation Streaming", text_color="#38bdf8")
            self.sim_thread = threading.Thread(target=self._run_simulation_loop, daemon=True)
            self.sim_thread.start()
        else:
            self.simulation_running = False
            self.btn_sim_toggle.configure(text="▶ Start Live Simulation", fg_color="#10b981", hover_color="#059669")
            self.lbl_status.configure(text="● System Online (Idle)", text_color="#10b981")

    def _run_simulation_loop(self):
        while self.simulation_running:
            self.system.simulate_telemetry_step()
            self.after(0, self.refresh_dashboard)
            time.sleep(2.0)

    def export_report_dialog(self):
        filepath = filedialog.asksaveasfilename(
            title="Export Municipal Summary Report",
            defaultextension=".txt",
            filetypes=[("Text Report", "*.txt"), ("Markdown Document", "*.md")]
        )
        if filepath:
            success = self.system.export_summary_report(filepath)
            if success:
                messagebox.showinfo("Export Successful", f"Executive water quality report saved to:\n{filepath}")
            else:
                messagebox.showerror("Export Failed", "Could not write the summary report file.")

    def clear_all_data(self):
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear all telemetry records and alerts?"):
            self.system.clear_data()
            self.refresh_dashboard()

    def open_threshold_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Configure Safety Thresholds")
        dialog.geometry("450x480")
        dialog.transient(self)
        dialog.grab_set()

        lbl_desc = ctk.CTkLabel(dialog, text="Adjust EPA / Municipal Safety Thresholds", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_desc.pack(pady=15)

        entries = {}
        frame_grid = ctk.CTkFrame(dialog, fg_color="transparent")
        frame_grid.pack(fill="x", padx=20, pady=5)

        for i, (metric, bounds) in enumerate(self.system.thresholds.items()):
            row_f = ctk.CTkFrame(frame_grid, fg_color="transparent")
            row_f.pack(fill="x", pady=4)

            m_lbl = ctk.CTkLabel(row_f, text=f"{metric.upper()} ({bounds['unit']}):", width=140, anchor="w")
            m_lbl.pack(side="left")

            min_ent = ctk.CTkEntry(row_f, width=80, placeholder_text="Min")
            min_ent.insert(0, str(bounds.get("min", "")))
            min_ent.pack(side="left", padx=5)

            max_ent = ctk.CTkEntry(row_f, width=80, placeholder_text="Max")
            max_ent.insert(0, str(bounds.get("max", "")))
            max_ent.pack(side="left", padx=5)

            entries[metric] = (min_ent, max_ent)

        def save_thresholds():
            for m, (ent_min, ent_max) in entries.items():
                try:
                    val_min = float(ent_min.get().strip()) if ent_min.get().strip() != "" else None
                    val_max = float(ent_max.get().strip()) if ent_max.get().strip() != "" else None
                    self.system.update_threshold(m, val_min, val_max)
                except ValueError:
                    messagebox.showerror("Input Error", f"Invalid numeric value for {m}")
                    return
            messagebox.showinfo("Saved", "Safety thresholds updated successfully.")
            dialog.destroy()
            self.refresh_dashboard()

        btn_save = ctk.CTkButton(dialog, text="Save Threshold Changes", command=save_thresholds, fg_color="#0284c7")
        btn_save.pack(pady=20)

if __name__ == "__main__":
    app = MunicipalWaterApp()
    app.mainloop()
