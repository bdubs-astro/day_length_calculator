'''
Create a polar plot showing the daylight hours for the specified date and location.

Uses the astral library to calculate the sunrise, sunset, and twilight times.
The depression angle (i.e., the angle of the Sun's geometric center below the horizon for 
the twilight calculation) is adjustable. By default, it is set to 6°, which corresponds to 
civil twilight. Other common values are 12° (nautical twilight) and 18° (astronomical twilight).

https://pypi.org/project/astral/

https://sffjunkie.github.io/astral/

https://www.weather.gov/fsd/twilight

Uses the pytz library to create timezone-aware datetime objects.

https://pypi.org/project/pytz/

https://pypi.org/project/DateTime/

https://pytutorial.com/python-pytz-time-zone-handling-made-easy/
'''

from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import (
        QApplication, QMainWindow, QMessageBox, QVBoxLayout,
        QWidget, QMenuBar, QMenu, QStatusBar, QLabel,
        QDialog, QLineEdit, QPushButton, QDateEdit,
        QTableWidget, QTableWidgetItem
)
from PySide6.QtCore import QDate, Qt

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from matplotlib.projections.polar import PolarAxes

import numpy as np
import sys
import os
from typing import cast
from datetime import datetime
import pytz
from astral import LocationInfo
from astral.sun import sun

# Icon filename
icon_fname = 'bw.ico'

# TODO: move inside DayLengthCalculator class ???
def time_to_angle(value):
    '''
    **Convert a time object to an angle in radians.**
    '''
    if isinstance(value, dict):
        return {k: time_to_angle(v) for k, v in value.items()}  # Recursively process dicts
    return (value.hour + value.minute / 60) / 24 * 2 * np.pi


class BaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

    # todo: merge with version in DayLengthCalculator class ???
    def show_message(self, message: str, icon_type: QMessageBox.Icon) -> None:
        '''
        **Display a message using the *QMessageBox* class.**

        :param message: The text that appears in the box.
        :type message: str
        :param icon_type: The icon that appears in the box, *e.g.*, *QMessageBox.Warning*.
        :type icon_type: QMessageBox.Icon
        '''
        msg_box = QMessageBox(self)
        msg_box.setText(message)
        msg_box.setIcon(icon_type)
        msg_box.setWindowTitle("Day Length Calculator")

        # Ensure text wraps properly
        msg_box.setMinimumSize(300, 200)  # Adjust width/height as needed
        msg_box.setSizeGripEnabled(True)  # Allow resizing
     
        # Adjust the QLabel inside the message box
        label = msg_box.findChild(QLabel, "qt_msgbox_label")
        if label:
            label.setMinimumWidth(200)
            label.setWordWrap(True)
            label.adjustSize()
            msg_box.resize(max(label.sizeHint().width() + 50, 200), msg_box.height())

        msg_box.exec()


class TimeZoneDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Common Time Zones")
        self.setFixedSize(300, 300)  # width, height

        self.table = QTableWidget()

        # data for the table
        time_zones = [
            ["UTC", "Europe/Paris", "Europe/London", "US/Eastern", "US/Central", "US/Mountain", "US/Arizona", "US/Pacific"],
            ["0", "+1 / +2", "0 / +1", "-5 / -4", "-6 / -5", "-7 / -6", "-7 / -7", "-8 / -7"],
            ["UTC", "CET / CEST", "GMT / BST", "EST / EDT", "CST / CDT", "MST / MDT", "MST", "PST / PDT"],
        ]

        # Set table size (number of rows and columns)
        self.table.setRowCount(len(time_zones[0]))
        self.table.setColumnCount(3)

        self.table.setVerticalHeaderLabels([])  # Hide row numbers
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalHeaderLabels(["Identifier", "GMT Offset", "Abbreviation"])
        self.table.horizontalHeader().setVisible(True)

        # Populate the table 
        for col_idx, col in enumerate(time_zones):
            for row_idx, tz in enumerate(col):
                item = QTableWidgetItem(tz)
                # Center align text in the second column
                if col_idx == 1 or col_idx == 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_idx, col_idx, item)
        self.table.resizeColumnsToContents()

        layout = QVBoxLayout()
        layout.addWidget(self.table, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)


class LocationDialog(BaseDialog):
    # Class attributes to retain last entered values
    last_location_name = None
    last_latitude = None
    last_longitude = None
    last_tz_str = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Location")
        self.setWindowIcon(QIcon(icon_fname))
        self.setFixedSize(300, 250)

        layout = QVBoxLayout(self)

        # Default values (used only the first time through)
        default_location_name = "Ann Arbor" 
        default_latitude = 42.22530
        default_longitude = -83.74567
        default_tz_str = "US/Eastern"

        # Use previous values if available, otherwise use defaults
        self.location_name = LocationDialog.last_location_name if LocationDialog.last_location_name is not None else default_location_name
        self.latitude = LocationDialog.last_latitude if LocationDialog.last_latitude is not None else default_latitude
        self.longitude = LocationDialog.last_longitude if LocationDialog.last_longitude is not None else default_longitude
        self.tz_str = LocationDialog.last_tz_str if LocationDialog.last_tz_str is not None else default_tz_str

        # Input fields
        self.loc_label = QLabel("Name")
        self.loc_input = QLineEdit(str(self.location_name))  # Pre-fill with last or default

        self.lat_label = QLabel("Latitude (°.dddd)")
        self.lat_input = QLineEdit(str(self.latitude))  # Pre-fill with last or default

        self.lon_label = QLabel("Longitude (°.dddd)")
        self.lon_input = QLineEdit(str(self.longitude))  # Pre-fill with last or default

        self.tz_label = QLabel("TZ Identifier (see list ...)")
        self.tz_input = QLineEdit(str(self.tz_str))  # Pre-fill with last or default

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)

        layout.addWidget(self.loc_label)
        layout.addWidget(self.loc_input)
        layout.addWidget(self.lat_label)
        layout.addWidget(self.lat_input)
        layout.addWidget(self.lon_label)
        layout.addWidget(self.lon_input)
        layout.addWidget(self.tz_label)
        layout.addWidget(self.tz_input)
        layout.addWidget(self.ok_button)

    def accept(self):
        """Store entered values and close dialog."""
        try:
            LocationDialog.last_latitude = float(self.lat_input.text())
            LocationDialog.last_longitude = float(self.lon_input.text())
            LocationDialog.last_location_name = self.loc_input.text().strip()
            tz_str = self.tz_input.text().strip()
            if tz_str not in pytz.all_timezones:
                raise ValueError("Invalid timezone input.")
            LocationDialog.last_tz_str = tz_str
            super().accept()
        except ValueError as e:
            self.show_message(str(e), QMessageBox.Warning) # type: ignore


    def get_lat_lon(self):
        try:
            lat_text = self.lat_input.text().strip()
            lon_text = self.lon_input.text().strip()

            if not lat_text or not lon_text:
                return None, None  # Prevent crashing on empty input

            lat = float(lat_text)
            lon = float(lon_text)

            if -90 <= lat <= 90 and -180 <= lon <= 180:  # Validate range
                return lat, lon
            else:
                return None, None  # Invalid range
        except ValueError:
            return None, None


class DateEntryDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Date")
        self.setWindowIcon(QIcon(icon_fname))
                       
        layout = QVBoxLayout(self)

        # todo: add the ability to remember the last date entered instead of defaulting to current???
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())  # Set default date
        self.date_edit.setFixedWidth(150)  # Set a fixed width to make it compact

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)

        layout.addWidget(self.date_edit)
        layout.addWidget(self.ok_button)
        self.setLayout(layout)

    def get_selected_date(self):
        qdate = self.date_edit.date()
        return datetime(qdate.year(), qdate.month(), qdate.day())


class DayLengthCalculator(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Day Length Calculator")

        self.target_date = None
        self.location = None

        # Set the icon
        if getattr(sys, 'frozen', False):  # If bundled with PyInstaller
            icon_path = os.path.join(sys._MEIPASS, icon_fname)  # type: ignore
        else:
            icon_path = icon_fname
        self.setWindowIcon(QIcon(icon_path))

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout for the central widget
        layout = QVBoxLayout(central_widget)

        # Matplotlib figure and canvas
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Add Matplotlib navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)

        # Create menu bar
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)

        # Create status bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        # menu
        menu = QMenu("Menu", self)
        self.menu_bar.addMenu(menu)

        # Select the date action
        select_date_action = QAction('Select date', self)
        select_date_action.setShortcut('Ctrl+D')
        select_date_action.setStatusTip('Select a date.')
        select_date_action.triggered.connect(self.select_date)
        menu.addAction(select_date_action)

        # Select the location action
        select_location_action = QAction('Select location', self)
        select_location_action.setShortcut('Ctrl+L')
        select_location_action.setStatusTip('Select a location.')
        select_location_action.triggered.connect(self.select_location)
        menu.addAction(select_location_action)

        # todo: add reset defaults action???

        # Update Plot action
        update_plot_action = QAction('Update plot', self)
        update_plot_action.setShortcut('Ctrl+U')
        update_plot_action.setStatusTip('Update the plot.')
        update_plot_action.triggered.connect(self.update_plot)
        menu.addAction(update_plot_action)

        # Show time zones action
        show_tz_action = QAction("Show time zones", self)
        show_tz_action.setShortcut('Ctrl+Z')
        show_tz_action.setStatusTip('Table containing selected time zones.')
        show_tz_action.triggered.connect(self.show_time_zones)
        menu.addAction(show_tz_action)

        # Exit action
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+X')
        exit_action.setStatusTip('Exit the application.')
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)

    def show_message(self, message: str, icon_type: QMessageBox.Icon) -> None:
        '''
        **Display a message using the *QMessageBox* class.**

        :param message: The text that appears in the box.
        :type message: str
        :param icon_type: The icon that appears in the box, *e.g.*, *QMessageBox.Warning*.
        :type icon_type: QMessageBox.Icon
        '''
        msg_box = QMessageBox(self)
        msg_box.setText(message)
        msg_box.setIcon(icon_type)
        msg_box.setWindowTitle("Day Length Calculator")

        # Ensure text wraps properly
        msg_box.setMinimumSize(300, 200)  # Adjust width/height as needed
        msg_box.setSizeGripEnabled(True)  # Allow resizing
     
        # Adjust the QLabel inside the message box
        label = msg_box.findChild(QLabel, "qt_msgbox_label")
        if label:
            label.setMinimumWidth(200)
            label.setWordWrap(True)
            label.adjustSize()
            msg_box.resize(max(label.sizeHint().width() + 50, 200), msg_box.height())

        msg_box.exec()

    def show_time_zones(self):
        self.dialog = TimeZoneDialog(self)
        self.dialog.exec()

    def select_date(self):
        dialog = DateEntryDialog()

        if dialog.exec():  # Waits for user input
            self.target_date = dialog.get_selected_date()
        else:
            message = "Invalid date input."
            self.show_message(message, QMessageBox.Warning) # type: ignore

    def select_location(self):

        dialog = LocationDialog(self)

        if dialog.exec():  # If user clicks OK
            lat, lon = dialog.get_lat_lon()
            if lat is not None and lon is not None:
                self.latitude = lat
                self.longitude = lon
                self.location_name = dialog.loc_input.text().strip()
                self.region = ""
                self.tz_str = dialog.tz_input.text().strip()
                self.location = LocationInfo(
                    self.location_name, 
                    self.region, 
                    self.tz_str, 
                    self.latitude, 
                    self.longitude
                )
                self.tz = pytz.timezone(self.location.timezone)  # pytz timezone object - see https://pypi.org/project/pytz/
            else:
                message = "Invalid latitude/longitude input."
                self.show_message(message, QMessageBox.Warning)  # type: ignore
 
    def get_sun_info(self, twilight_depression: float):
        # Get sunrise, sunset, and twilight times

        if self.location is None:
            self.show_message("No location selected.", QMessageBox.Warning) # type: ignore
            return

        try:
            self.sun_info: dict = sun(
                self.location.observer, 
                date = self.target_date, 
                tzinfo = self.tz, 
                dawn_dusk_depression = twilight_depression
            )
            # print(f"Sun info for depression angle {twilight_depression}: {self.sun_info}")  # ! Debug print

        except ValueError as e:
            print(f"ValueError: {e}")
            return  # Exit the function
        except Exception as e:
            print(f"Error: {e}")
            return  # Exit the function
        
    def update_plot(self):

        if self.target_date is None:
            self.show_message("No date selected.", QMessageBox.Warning)  # type: ignore
            return

        if self.location is None:
            self.show_message("No location selected.", QMessageBox.Warning) # type: ignore
            return

        # Get sunrise, sunset, and solar noon times
        self.get_sun_info(0)

        # Store in a dictionary
        event_times = {
            'noon': self.sun_info.get('noon', None),
            'sunrise': self.sun_info.get('sunrise', None),
            'sunset': self.sun_info.get('sunset', None),
        }

        # Get the different twilight times
        depression_angles = {
            "dusk_civil": 6,  # Civil twilight angle
            "dusk_nautical": 12,  # Nautical twilight angle
            "dusk_astro": 18,  # Astronomical twilight angle
        }

        # Loop through the depression angles and call get_sun_info() for each
        twilight_times = {}
        for twilight_type, depression in depression_angles.items():
            self.get_sun_info(twilight_depression=depression)
            
            # Store the dawn and dusk times for the current twilight type
            twilight_times[twilight_type] = {
                'dawn': self.sun_info.get('dawn', None),
                'dusk': self.sun_info.get('dusk', None)
            }

        # Combine the two dictionaries
        sun_data = {**event_times, **twilight_times}

        # Convert standard solar times (sunrise, sunset, noon) to angles
        angles = {}
        angles.update({k: time_to_angle(v.time()) for k, v in sun_data.items() if isinstance(v, datetime)})

        # Convert twilight times and flatten keys (nested dictionaries)
        for twilight_type, times in sun_data.items():
            if isinstance(times, dict):  # Only process nested twilight dicts
                for key, value in times.items():
                    # Simplify the naming, using just the event (e.g., 'civil_dawn', 'civil_dusk')
                    angles[f"{twilight_type.split('_')[1]}_{key}"] = time_to_angle(value.time())  # Extract time part from datetime

        # print(twilight_times)  # ! debug print
        # print(sun_data)  # ! debug print
        # print(angles)  # ! debug print

        # construct plot
        self.figure.clear()
        ax = self.figure.add_subplot(111, projection='polar')
        ax = cast(PolarAxes, ax)
        ax.set_theta_zero_location('N')  # Midnight at top
        ax.set_theta_direction(-1)  # Clockwise rotation

        # Full circle for reference
        full_circle = 2 * np.pi

        # add solar noon and midnight lines to the plot
        ax.plot([angles['noon'], angles['noon']], [0, 1], color='white', linestyle=':', linewidth=2, alpha=0.8)
        ax.plot([angles['noon'] + np.pi, angles['noon'] + np.pi], [0, 1], color='black', linestyle=':', linewidth=2, alpha=0.8)

        fill_colors = ['gold', '#0073CF', '#0000CD', '#00008B', '#00004B'] 

        # Fill daylight region
        daylight_width = (angles['sunset'] - angles['sunrise']) % full_circle
        ax.bar(angles['sunrise'], 1, width=daylight_width, color=fill_colors[0], alpha=0.8, align='edge')

        # Fill civil twilight regions
        civil_twilight_width_am = (angles['sunrise'] - angles['civil_dawn']) % full_circle
        ax.bar(angles['civil_dawn'], 1, width=civil_twilight_width_am, color=fill_colors[1], alpha=0.6, align='edge')
        civil_twilight_width_pm = (angles['civil_dusk'] - angles['sunset']) % full_circle
        ax.bar(angles['sunset'], 1, width=civil_twilight_width_pm, color=fill_colors[1], alpha=0.6, align='edge')

        # Fill nautical twilight regions
        naut_twilight_width_am = (angles['civil_dawn'] - angles['nautical_dawn']) % full_circle
        ax.bar(angles['nautical_dawn'], 1, width=naut_twilight_width_am, color=fill_colors[2], alpha=0.8, align='edge')
        naut_twilight_width_pm = (angles['nautical_dusk'] - angles['civil_dusk']) % full_circle
        ax.bar(angles['civil_dusk'], 1, width=naut_twilight_width_pm, color=fill_colors[2], alpha=0.8, align='edge')

        # Fill astronomical twilight regions
        astro_twilight_width_am = (angles['nautical_dawn'] - angles['astro_dawn']) % full_circle
        ax.bar(angles['astro_dawn'], 1, width=astro_twilight_width_am, color=fill_colors[3], alpha=0.8, align='edge')
        astro_twilight_width_pm = (angles['astro_dusk'] - angles['nautical_dusk']) % full_circle
        ax.bar(angles['nautical_dusk'], 1, width=astro_twilight_width_pm, color=fill_colors[3], alpha=0.8, align='edge')

        # Fill nighttime region
        night_width = (angles['astro_dawn'] - angles['astro_dusk']) % full_circle
        ax.bar(angles['astro_dusk'], 1, width=night_width, color=fill_colors[4], alpha=0.8, align='edge')

        # Set Hour Labels (24-hour format)
        hour_labels = [f"{h}:00" for h in range(24)]
        ax.set_xticks(np.linspace(0, 2*np.pi, 24, endpoint=False))
        ax.set_xticklabels(hour_labels, fontsize=9)

        ax.set_yticks([])
        ax.set_yticklabels([])
        ax.yaxis.grid(False)
        ax.xaxis.grid(False)

        r_values = [1, 1.05]  # Slightly outside the filled area
        for angle in np.linspace(0, 2*np.pi, 24, endpoint=False):
            ax.plot([angle, angle], r_values, color='black', linewidth=0.8, linestyle='solid')

        # Draw the outer circle at r = 1.05
        outer_circle = np.linspace(0, full_circle, 100)
        ax.plot(outer_circle, np.full_like(outer_circle, 1.05), color='black', linewidth=1.2)

        # Title
        loc_str = self.location.name[:13] + '...' if len(self.location.name) > 15 else self.location.name
        date_str = self.target_date.strftime("%m/%d/%Y")  # Format: MM/DD/YYYY
        ax.set_title(f"{date_str}: {loc_str} ({self.latitude:.3f}°, {self.longitude:.3f}°, TZ: {self.tz_str})", pad=35, fontsize=12)

        # Display length of the day
        day_length = self.sun_info['sunset'] - self.sun_info['sunrise']
        day_length_str = str(day_length).split('.')[0]

        # Display sunrise and sunset times
        sunrise_time_str = self.sun_info['sunrise'].strftime("%H:%M")
        sunset_time_str = self.sun_info['sunset'].strftime("%H:%M")

        # Add text annotations for sunrise and sunset
        self.figure.text(0.5, 0.02, f"Sunrise: {sunrise_time_str}    Sunset: {sunset_time_str}    Day Length: {day_length_str}", 
            ha='center', fontsize=11)

        # Apply plot layout adjustments
        self.figure.subplots_adjust(top=0.85, bottom=0.13, left=0.125, right=0.9, hspace=0.2, wspace=0.2)

        self.canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DayLengthCalculator()
    window.resize(600, 600)
    window.show()
    sys.exit(app.exec())
