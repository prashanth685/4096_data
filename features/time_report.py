from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, QDateTimeEdit, QListWidget, 
                             QListWidgetItem, QPushButton, QTextEdit, QSizePolicy)
from PyQt5.QtCore import Qt, QDateTime
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import logging
from datetime import datetime
import numpy as np

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TimeReportFeature:
    def __init__(self, parent, db, project_name):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.widget = QWidget()
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.dragging = False
        self.press_x = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        header = QLabel(f"TIME REPORT FOR {self.project_name.upper()}")
        header.setStyleSheet("color: white; font-size: 26px; font-weight: bold; padding: 8px;")
        layout.addWidget(header, alignment=Qt.AlignCenter)

        self.time_report_widget = QWidget()
        self.time_report_layout = QVBoxLayout()
        self.time_report_widget.setLayout(self.time_report_layout)
        self.time_report_widget.setStyleSheet("background-color: #2c3e50; border-radius: 5px; padding: 10px;")

        # Filter layout with date-time pickers and tag list
        filter_layout = QHBoxLayout()
        
        from_label = QLabel("From:")
        from_label.setStyleSheet("color: white; font-size: 14px;")
        self.time_from_date = QDateTimeEdit()
        self.time_from_date.setCalendarPopup(True)
        self.time_from_date.setDateTime(QDateTime.currentDateTime().addDays(-1))
        self.time_from_date.setStyleSheet("background-color: #34495e; color: white; border: 1px solid #1a73e8; padding: 5px;")
        self.time_from_date.dateTimeChanged.connect(self.update_plot)
        
        to_label = QLabel("To:")
        to_label.setStyleSheet("color: white; font-size: 14px;")
        self.time_to_date = QDateTimeEdit()
        self.time_to_date.setCalendarPopup(True)
        self.time_to_date.setDateTime(QDateTime.currentDateTime())
        self.time_to_date.setStyleSheet("background-color: #34495e; color: white; border: 1px solid #1a73e8; padding: 5px;")
        self.time_to_date.dateTimeChanged.connect(self.update_plot)
        
        tag_label = QLabel("Select Tags:")
        tag_label.setStyleSheet("color: white; font-size: 14px;")
        self.time_report_tag_list = QListWidget()
        self.time_report_tag_list.setSelectionMode(QListWidget.MultiSelection)
        tags_data = list(self.db.tags_collection.find({"project_name": self.project_name}))
        if not tags_data:
            self.time_report_tag_list.addItem("No Tags Available")
        else:
            for tag in tags_data:
                item = QListWidgetItem(tag["tag_name"])
                self.time_report_tag_list.addItem(item)
        self.time_report_tag_list.setStyleSheet("background-color: #34495e; color: white; border: 1px solid #1a73e8; padding: 5px;")
        self.time_report_tag_list.itemSelectionChanged.connect(self.update_plot)

        filter_layout.addWidget(from_label)
        filter_layout.addWidget(self.time_from_date)
        filter_layout.addWidget(to_label)
        filter_layout.addWidget(self.time_to_date)
        filter_layout.addWidget(tag_label)
        filter_layout.addWidget(self.time_report_tag_list)
        filter_layout.addStretch()
        self.time_report_layout.addLayout(filter_layout)

        # Add canvas for plotting
        self.time_report_layout.addWidget(self.canvas)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_drag)

        # Button layout
        button_layout = QHBoxLayout()
        pdf_btn = QPushButton("Export to PDF")
        pdf_btn.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; border: none; padding: 5px; border-radius: 5px; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        pdf_btn.clicked.connect(lambda: self.export_time_report_to_pdf(self.project_name))

        reset_btn = QPushButton("Reset View")
        reset_btn.setStyleSheet("""
            QPushButton { background-color: #f39c12; color: white; border: none; padding: 5px; border-radius: 5px; }
            QPushButton:hover { background-color: #e67e22; }
        """)
        reset_btn.clicked.connect(self.reset_view)

        button_layout.addWidget(pdf_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        self.time_report_layout.addLayout(button_layout)

        # Result text area
        self.time_report_result = QTextEdit()
        self.time_report_result.setReadOnly(True)
        self.time_report_result.setStyleSheet("background-color: #34495e; color: white; border-radius: 5px; padding: 10px;")
        self.time_report_result.setMinimumHeight(100)
        self.time_report_result.setText(f"Time Report for {self.project_name}: Select tags to start plotting.\nUse mouse wheel to zoom, drag to pan.")
        self.time_report_layout.addWidget(self.time_report_result)
        self.time_report_layout.addStretch()

        layout.addWidget(self.time_report_widget)

        # Initial setup
        if tags_data:
            self.time_report_tag_list.item(0).setSelected(True)
            self.update_plot()

    def update_plot(self):
        selected_tags = [item.text() for item in self.time_report_tag_list.selectedItems()]
        if not selected_tags or "No Tags Available" in selected_tags:
            self.time_report_result.setText("No valid tags selected.")
            self.figure.clear()
            self.canvas.draw()
            return

        from_dt = self.time_from_date.dateTime().toPyDateTime()
        to_dt = self.time_to_date.dateTime().toPyDateTime()

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        colors = ['b', 'r', 'g', 'y', 'm', 'c']  # Color cycle for multiple tags

        report = f"Time Report for {self.project_name} ({from_dt.isoformat()} to {to_dt.isoformat()}):\n"
        report += f"Selected Tags: {', '.join(selected_tags)}\n\n"

        for i, tag in enumerate(selected_tags):
            data = self.db.get_tag_values(self.project_name, tag)
            try:
                filtered_data = [
                    entry for entry in data
                    if from_dt <= datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%S.%f") <= to_dt
                ]
            except ValueError as e:
                logging.error(f"Error parsing timestamp for tag {tag}: {e}")
                continue

            if filtered_data:
                timestamps = []
                values = []
                for entry in filtered_data:
                    dt = datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%S.%f")
                    timestamps.extend([dt] * len(entry["values"]))
                    values.extend(entry["values"])

                if timestamps and values:
                    ax.plot(timestamps, values, f'{colors[i % len(colors)]}-', label=tag, linewidth=1.5)

                report += f"Tag: {tag}\n"
                report += f"  Messages in Range: {len(filtered_data)}\n"
                report += f"  Latest Value: {filtered_data[-1]['values'][-1]}\n"
                report += f"  Sample Data (last 5 entries):\n"
                for entry in filtered_data[-5:]:
                    report += f"    {entry['timestamp']}: {entry['values'][-5:]}\n"
            else:
                report += f"Tag: {tag}\n  No data in selected time range.\n"

        ax.grid(True, linestyle='--', alpha=0.7)
        ax.set_xlabel("Time")
        ax.set_ylabel("Values")
        ax.legend()
        ax.tick_params(axis='x', rotation=45)
        self.figure.tight_layout()
        self.canvas.draw()
        self.time_report_result.setText(report)
        logging.debug(f"Time report and plot updated for tags: {selected_tags}")

    def reset_view(self):
        self.update_plot()  # Simply redraw with current settings
        logging.debug("Time report view reset")

    def on_scroll(self, event):
        if event.inaxes:
            ax = event.inaxes
            xlim = ax.get_xlim()
            x_range = xlim[1] - xlim[0]
            center = event.xdata if event.xdata is not None else (xlim[0] + xlim[1]) / 2
            scale = 1.1 if event.button == 'down' else 0.9
            new_range = x_range * scale
            new_left = center - new_range / 2
            new_right = center + new_range / 2
            ax.set_xlim(new_left, new_right)
            self.canvas.draw()
            logging.debug(f"Zoomed: new window size {new_range:.2f}")

    def on_press(self, event):
        if event.inaxes and event.button == 1:
            self.dragging = True
            self.press_x = event.xdata

    def on_release(self, event):
        self.dragging = False

    def on_drag(self, event):
        if self.dragging and event.inaxes:
            ax = event.inaxes
            if self.press_x is not None and event.xdata is not None:
                dx = self.press_x - event.xdata
                xlim = ax.get_xlim()
                ax.set_xlim(xlim[0] + dx, xlim[1] + dx)
                self.press_x = event.xdata
                self.canvas.draw()
                logging.debug(f"Panned: new xlim [{xlim[0] + dx:.2f}, {xlim[1] + dx:.2f}]")

    def export_time_report_to_pdf(self, project_name):
        try:
            report_text = self.time_report_result.toPlainText()
            logging.info(f"Exporting time report for {project_name} to PDF:\n{report_text[:100]}...")
            # Add basic PDF export (requires reportlab or similar library)
            # For now, just append a message
            self.time_report_result.setText(f"{report_text}\n\n[Export to PDF functionality not fully implemented yet.]")
        except Exception as e:
            logging.error(f"Failed to export time report to PDF: {str(e)}")
            self.time_report_result.setText(f"Error exporting to PDF: {str(e)}")

    def get_widget(self):
        return self.widget
