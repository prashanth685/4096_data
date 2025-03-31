from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QPushButton, QTextEdit, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from collections import deque
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TimeViewFeature:
    def __init__(self, parent, db, project_name):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.widget = QWidget()
        self.mqtt_tag = None
        self.max_buffer_size = 8192  # Increased buffer size to handle rapid data bursts
        self.time_view_buffer = deque(maxlen=self.max_buffer_size)
        self.time_view_timestamps = deque(maxlen=self.max_buffer_size)
        self.timer = QTimer(self.widget)
        self.timer.timeout.connect(self.update_time_view_plot)
        self.figure = plt.Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.dragging = False
        self.press_x = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        header = QLabel(f"TIME VIEW FOR {self.project_name.upper()}")
        header.setStyleSheet("color: white; font-size: 26px; font-weight: bold; padding: 8px;")
        layout.addWidget(header, alignment=Qt.AlignCenter)

        self.time_widget = QWidget()
        self.time_layout = QVBoxLayout()
        self.time_widget.setLayout(self.time_layout)
        self.time_widget.setStyleSheet("background-color: #2c3e50; border-radius: 5px; padding: 10px;")
        self.time_widget.setMinimumHeight(600)

        tag_layout = QHBoxLayout()
        tag_label = QLabel("Select Tag:")
        tag_label.setStyleSheet("color: white; font-size: 14px;")
        self.tag_combo = QComboBox()
        tags_data = list(self.db.tags_collection.find({"project_name": self.project_name}))
        if not tags_data:
            self.tag_combo.addItem("No Tags Available")
        else:
            for tag in tags_data:
                self.tag_combo.addItem(tag["tag_name"])
        self.tag_combo.setStyleSheet("background-color: #34495e; color: white; border: 1px solid #1a73e8; padding: 5px;")
        self.tag_combo.currentTextChanged.connect(self.setup_time_view_plot)

        reset_btn = QPushButton("Reset")
        reset_btn.setStyleSheet("""
            QPushButton { background-color: #f39c12; color: white; border: none; padding: 5px; border-radius: 5px; }
            QPushButton:hover { background-color: #e67e22; }
        """)
        reset_btn.clicked.connect(self.reset_time_view)

        tag_layout.addWidget(tag_label)
        tag_layout.addWidget(self.tag_combo)
        tag_layout.addWidget(reset_btn)
        tag_layout.addStretch()
        self.time_layout.addLayout(tag_layout)

        self.time_layout.addWidget(self.canvas)

        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_drag)

        self.time_result = QTextEdit()
        self.time_result.setReadOnly(True)
        self.time_result.setStyleSheet("background-color: #34495e; color: white; border-radius: 5px; padding: 10px;")
        self.time_result.setMinimumHeight(100)
        self.time_result.setText(
            f"Time View for {self.project_name}: Select a tag to start real-time plotting.\n"
            "Use mouse wheel to zoom, drag to pan, or reset to default."
        )
        self.time_layout.addWidget(self.time_result)
        self.time_layout.addStretch()

        layout.addWidget(self.time_widget)

        if tags_data:
            self.tag_combo.setCurrentIndex(0)
            self.setup_time_view_plot(self.tag_combo.currentText())

    def setup_time_view_plot(self, tag_name):
        if not self.project_name or not tag_name or tag_name == "No Tags Available":
            logging.warning("No project or valid tag selected for Time View!")
            return

        self.mqtt_tag = tag_name
        self.timer.stop()
        self.timer.setInterval(100)  # Adjust interval for faster updates
        self.time_view_buffer.clear()
        self.time_view_timestamps.clear()

        data = self.db.get_tag_values(self.project_name, self.mqtt_tag)
        if data:
            for entry in data[-2:]:
                self.time_view_buffer.extend(entry["values"])
                self.time_view_timestamps.extend([entry["timestamp"]] * len(entry["values"]))

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.line, = self.ax.plot([], [], 'b-', linewidth=1.5, color='darkblue')
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self.ax.set_ylabel("Values", rotation=90, labelpad=10)
        self.ax.yaxis.set_label_position("right")
        self.ax.yaxis.tick_right()
        self.ax.set_xlabel("Time (HH:MM:SSS)")
        self.ax.set_xlim(0, 1)
        self.ax.set_xticks(np.linspace(0, 1, 10))

        self.annotation = self.ax.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
                                           bbox=dict(boxstyle="round", fc="w"), arrowprops=dict(arrowstyle="->"))
        self.annotation.set_visible(False)

        self.figure.subplots_adjust(left=0.05, right=0.85, top=0.95, bottom=0.15)
        self.canvas.setMinimumSize(1000, 600)
        self.canvas.draw()
        self.timer.start()

    def generate_y_ticks(self, values):
        if not values:
            return np.arange(16390, 46538, 5000)
        y_max = max(values, default=46537)
        y_min = min(values, default=16390)
        padding = (y_max - y_min) * 0.1 if y_max != y_min else 5000
        y_max += padding
        y_min -= padding
        range_val = y_max - y_min
        step = max(range_val / 10, 1)
        step = np.ceil(step / 500) * 500
        ticks = []
        current = np.floor(y_min / step) * step
        while current <= y_max:
            ticks.append(current)
            current += step
        return ticks

    def update_time_view_plot(self):
        if not self.project_name or not self.mqtt_tag:
            self.time_result.setText("No project or tag selected for Time View.")
            return

        current_buffer_size = len(self.time_view_buffer)
        if current_buffer_size < 2:  # Minimum points needed for plotting
            self.time_result.setText(
                f"Waiting for sufficient data for {self.mqtt_tag} (Current buffer: {current_buffer_size}/{self.max_buffer_size})."
            )
            return

        xlim = self.ax.get_xlim()
        window_size = xlim[1] - xlim[0]

        # Calculate samples based on current buffer size and window
        samples_per_window = min(current_buffer_size, int(self.max_buffer_size * window_size))
        if samples_per_window < 2:
            samples_per_window = 2  # Ensure at least 2 points for plotting

        window_values = list(self.time_view_buffer)[-samples_per_window:]
        window_timestamps = list(self.time_view_timestamps)[-samples_per_window:]

        time_points = np.linspace(xlim[0], xlim[1], samples_per_window)
        self.line.set_data(time_points, window_values)

        y_max = max(window_values)
        y_min = min(window_values)
        padding = (y_max - y_min) * 0.1 if y_max != y_min else 5000
        self.ax.set_ylim(y_min - padding, y_max + padding)
        self.ax.set_yticks(self.generate_y_ticks(window_values))

        if window_timestamps:
            latest_dt = datetime.strptime(window_timestamps[-1], "%Y-%m-%dT%H:%M:%S.%f")
            time_labels = []
            tick_positions = np.linspace(xlim[0], xlim[1], 10)
            for tick in tick_positions:
                delta_seconds = tick - xlim[1]
                tick_dt = latest_dt + timedelta(seconds=delta_seconds)
                milliseconds = tick_dt.microsecond // 1000
                time_labels.append(f"{tick_dt.strftime('%H:%M:')}{milliseconds:03d}")
            self.ax.set_xticks(tick_positions)
            self.ax.set_xticklabels(time_labels, rotation=0)

        for txt in self.ax.texts:
            txt.remove()

        self.canvas.draw_idle()  # Use draw_idle for better performance
        self.time_result.setText(
            f"Time View Data for {self.mqtt_tag}, Latest value: {window_values[-1]}, "
            f"Window: {window_size:.2f}s, Buffer: {current_buffer_size}"
        )

    def reset_time_view(self):
        if hasattr(self, 'ax'):
            self.ax.set_xlim(0, 1)
            self.ax.set_xticks(np.linspace(0, 1, 10))
            self.canvas.draw()
            logging.debug("Time View reset to default 1-second window with 10 ticks")

    def on_mouse_move(self, event):
        if event.inaxes == self.ax:
            x, y = event.xdata, event.ydata
            if x is not None and y is not None:
                xlim = self.ax.get_xlim()
                window_size = xlim[1] - xlim[0]
                current_buffer_size = len(self.time_view_buffer)
                samples_per_window = min(current_buffer_size, int(self.max_buffer_size * window_size))
                idx = int(round((x - xlim[0]) / window_size * (samples_per_window - 1)))
                window_values = list(self.time_view_buffer)[-samples_per_window:]
                if 0 <= idx < len(window_values):
                    value = window_values[idx]
                    self.annotation.xy = (x, y)
                    self.annotation.set_text(f"Value: {value:.2f}")
                    self.annotation.set_visible(True)
                    self.canvas.draw_idle()
            else:
                self.annotation.set_visible(False)
                self.canvas.draw_idle()

    def on_scroll(self, event):
        if event.inaxes:
            ax = event.inaxes
            xlim = ax.get_xlim()
            x_range = xlim[1] - xlim[0]
            center = event.xdata if event.xdata is not None else (xlim[0] + xlim[1]) / 2
            scale = 1.1 if event.button == 'down' else 0.9
            new_range = x_range * scale
            if new_range < 0.1:
                new_range = 0.1
            elif new_range > 10:
                new_range = 10
            ax.set_xlim(center - new_range / 2, center + new_range / 2)
            self.canvas.draw_idle()
            logging.debug(f"Zoomed: new window size {new_range:.2f}s")

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
                new_left = xlim[0] + dx
                new_right = xlim[1] + dx
                if new_left < 0:
                    new_left = 0
                    new_right = new_left + (xlim[1] - xlim[0])
                ax.set_xlim(new_left, new_right)
                self.press_x = event.xdata
                self.canvas.draw_idle()
                logging.debug(f"Panned: new xlim [{new_left:.2f}, {new_right:.2f}]")

    def on_data_received(self, tag_name, values):
        if tag_name == self.mqtt_tag:
            self.time_view_buffer.extend(values)
            self.time_view_timestamps.extend([datetime.now().isoformat()] * len(values))
            logging.debug(f"Time View - Received {len(values)} values for {tag_name}")

    def get_widget(self):
        return self.widget