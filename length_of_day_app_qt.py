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
        QDialog, QLineEdit, QPushButton, QDateEdit
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
from datetime import datetime, time
import pytz
from astral import LocationInfo
from astral.sun import sun

# Icon filename
icon_fname = 'bw.ico'

# TODO: move inside DayLengthCalculator class ???
def time_to_angle(time: time) -> float:
    '''
    **Convert a time object to an angle in radians.**

    :param time: A time object representing the time of day (hours and minutes).
    :type time: time
    :return: A float representing the angle in radians corresponding to the time of day.
    :rtype: float
    '''
    return (time.hour + time.minute / 60) / 24 * 2 * np.pi


class BaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

    def show_message(self, message, icon_type):
        msg_box = QMessageBox(self)
        msg_box.setText(message)
        msg_box.setIcon(icon_type)
        msg_box.setWindowTitle("Day Length Calculator")
        # Adjust the message box width dynamically 
        msg_box.setMinimumWidth(80)  # Adjust width as needed
        msg_box.setSizeGripEnabled(True)  # Allow resizing if needed
        # Access the QLabel inside QMessageBox and set its minimum width
        label = msg_box.findChild(QLabel, "qt_msgbox_label")
        if label:
            label.setMinimumWidth(125)  # Adjust based on message length   
        msg_box.exec()


class LocationDialog(BaseDialog):
    # Class attributes to retain last entered values
    last_location_name = None
    last_latitude = None
    last_longitude = None
    last_tz_str = None
    # TODO: add twilight depression angle as a parameter

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
        self.loc_label = QLabel("Location:")
        self.loc_input = QLineEdit(str(self.location_name))  # Pre-fill with last or default

        self.lat_label = QLabel("Latitude:")
        self.lat_input = QLineEdit(str(self.latitude))  # Pre-fill with last or default

        self.lon_label = QLabel("Longitude:")
        self.lon_input = QLineEdit(str(self.longitude))  # Pre-fill with last or default

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)

        layout.addWidget(self.loc_label)
        layout.addWidget(self.loc_input)
        layout.addWidget(self.lat_label)
        layout.addWidget(self.lat_input)
        layout.addWidget(self.lon_label)
        layout.addWidget(self.lon_input)
        layout.addWidget(self.ok_button)

    def accept(self):
        """Store entered values and close dialog."""
        try:
            LocationDialog.last_latitude = float(self.lat_input.text())
            LocationDialog.last_longitude = float(self.lon_input.text())
            LocationDialog.last_location_name = self.loc_input.text().strip()
            LocationDialog.last_tz_str = self.tz_str
            super().accept()
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numeric values for latitude and longitude.")

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
        self.times = {}

        # Define twilight depression (angle below horizon for dawn/dusk calculation)
        self.twilight_depression = 6  # 6° = civil twilight

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

        # Update Plot action
        update_plot_action = QAction('Update plot', self)
        update_plot_action.setShortcut('Ctrl+U')
        update_plot_action.setStatusTip('Update the plot.')
        update_plot_action.triggered.connect(self.update_plot)
        menu.addAction(update_plot_action)

        # Exit action
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+X')
        exit_action.setStatusTip('Exit the application.')
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)

    def show_message(self, message, icon_type):
        msg_box = QMessageBox(self)
        msg_box.setText(message)
        msg_box.setIcon(icon_type)
        msg_box.setWindowTitle("Day Length Calculator")
        # Adjust the message box width dynamically 
        msg_box.setMinimumWidth(80)  # Adjust width as needed
        msg_box.setSizeGripEnabled(True)  # Allow resizing if needed
        # Access the QLabel inside QMessageBox and set its minimum width
        label = msg_box.findChild(QLabel, "qt_msgbox_label")
        if label:
            label.setMinimumWidth(125)  # Adjust based on message length        
        msg_box.exec()

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
                self.region = "User-defined"
                self.tz_str = "UTC"  # Adjust time zone logic as needed
                self.location = LocationInfo(
                    self.location_name, 
                    self.region, 
                    self.tz_str, 
                    self.latitude, 
                    self.longitude
                )
                self.tz = pytz.utc  # Adjust based on location if needed
                # self.tz = pytz.timezone(self.location.timezone)  # pytz timezone object - see https://pypi.org/project/pytz/
            else:
                message = "Invalid latitude/longitude input."
                self.show_message(message, QMessageBox.Warning)  # type: ignore
 
    def get_sun_info(self):
        # Get sunrise, sunset, and twilight times
        try:
            self.sun_info: dict = sun(
                self.location.observer, 
                date=self.target_date, 
                tzinfo=self.tz, 
                dawn_dusk_depression=self.twilight_depression
            )
        except ValueError as e:
            print(f"ValueError: {e}")
            return  # Exit the function
        except Exception as e:
            print(f"Error: {e}")
            return  # Exit the function
        
        # Extract event times
        self.times: dict = {
            "midnight": datetime.strptime("00:00", "%H:%M").time(),
            "noon": datetime.strptime("12:00", "%H:%M").time(),
            "sunrise": self.sun_info['sunrise'].time(),
            "sunset": self.sun_info['sunset'].time(),
            "first_light": self.sun_info['dawn'].time(),
            "last_light": self.sun_info['dusk'].time()
    }

    def update_plot(self):

        # Get sunrise, sunset, and twilight times
        self.get_sun_info()

        if self.target_date is None:
            self.show_message("No date selected.", QMessageBox.Warning)  # type: ignore
            return

        if self.location is None:
            self.show_message("No location selected.", QMessageBox.Warning) # type: ignore
            return
        
        self.figure.clear()
        ax = self.figure.add_subplot(111, projection='polar')
        ax = cast(PolarAxes, ax)
        ax.set_theta_zero_location('N')  # Midnight at top
        ax.set_theta_direction(-1)  # Clockwise rotation

        # Full circle for reference
        full_circle = 2 * np.pi

        angles = {k: time_to_angle(v) for k, v in self.times.items()}

        # Fill nighttime (dusk to dawn)
        night_width = (angles['first_light'] - angles['last_light']) % full_circle
        ax.bar(angles['last_light'], 1, width=night_width, color='darkblue', alpha=0.8, align='edge')

        # Fill twilight regions
        twilight_width1 = (angles['sunrise'] - angles['first_light']) % full_circle
        twilight_width2 = (angles['last_light'] - angles['sunset']) % full_circle
        ax.bar(angles['first_light'], 1, width=twilight_width1, color='midnightblue', alpha=0.6, align='edge')
        ax.bar(angles['sunset'], 1, width=twilight_width2, color='midnightblue', alpha=0.6, align='edge')

        # Fill daylight region (sunrise to sunset)
        daylight_width = (angles['sunset'] - angles['sunrise']) % full_circle
        ax.bar(angles['sunrise'], 1, width=daylight_width, color='gold', alpha=0.8, align='edge')

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
        title_str = self.location.name[:15] + '...' if len(self.location.name) > 15 else self.location.name
        date_str = self.target_date.strftime("%m/%d/%Y")  # Format: MM/DD/YYYY
        ax.set_title(f"{date_str}: {title_str} ({self.latitude:.3f}°, {self.longitude:.3f}°)", pad=35, fontsize=12)

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
