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
    QWidget, QMenuBar, QMenu, QStatusBar, QLabel, QHBoxLayout # TODO: remove unused imports
)

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

def time_to_angle(time: time) -> float:
    '''
    **Convert a time object to an angle in radians.**

    :param time: A time object representing the time of day (hours and minutes).
    :type time: time
    :return: A float representing the angle in radians corresponding to the time of day.
    :rtype: float
    '''
    return (time.hour + time.minute / 60) / 24 * 2 * np.pi

class DayLengthCalculator(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Day Length Calculator")
        self.target_date = None

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

        # select date action
        select_date_action = QAction('Select date', self)
        self.num_data_cols = 2
        select_date_action.setShortcut('Ctrl+D')
        select_date_action.setStatusTip('Select a date.')
        select_date_action.triggered.connect(self.select_date)
        menu.addAction(select_date_action)

        # Exit action
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+X')
        exit_action.setStatusTip('Exit the application.')
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)

    def select_date(self):
        # TODO: Create a date selection dialog
        self.target_date = datetime.today()

        if self.target_date is not None:
            self.update_plot()
        else:
            message = "Failed to select a valid date.\n"
            self.show_message(message, QMessageBox.Critical) # type: ignore

    def select_location(self):
        self.latitude: float = 42.22530
        self.longitude: float = -83.74567
        self.location_name: str = "Ann Arbor"
        self.region: str = "Michigan/USA"
        self.tz_str: str = "US/Eastern"
        # Define twilight depression (angle below horizon for dawn/dusk calculation)
        self.twilight_depression = 6  # 6° = civil twilight

        self.location = LocationInfo(
            self.location_name, 
            self.region, 
            self.tz_str, 
            self.latitude, 
            self.longitude
        )

        # Get timezone object
        self.tz = pytz.timezone(self.location.timezone)  # pytz timezone object - see https://pypi.org/project/pytz/

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

        # Get location information
        self.select_location()

        # Get sunrise, sunset, and twilight times
        self.get_sun_info()

        if self.target_date is None:
            self.show_message("No date selected.", QMessageBox.Warning)  # type: ignore
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

    def show_message(self, message, icon_type):
        msg_box = QMessageBox(self)
        msg_box.setText(message)
        msg_box.setIcon(icon_type)
        msg_box.setWindowTitle("Day Length Calculator")
        msg_box.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DayLengthCalculator()
    window.resize(600, 600)
    window.show()
    sys.exit(app.exec())
