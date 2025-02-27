'''
Create a plot showing the daylight hours for a given date and location.
'''
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.projections.polar import PolarAxes
from typing import cast
from astral import LocationInfo
from astral.sun import sun
from datetime import datetime, time
import pytz

def time_to_angle(time: time) -> float:
    '''
    **Convert a time object to an angle in radians.**

    :param time: A time object representing the time of day (hours and minutes).
    :type time: time
    :return: A float representing the angle in radians corresponding to the time of day.
    :rtype: float
    '''
    return (time.hour + time.minute / 60) / 24 * 2 * np.pi

def _create_plot(
        times: dict, 
        location: LocationInfo, 
        target_date: datetime, 
        my_latitude: float, 
        my_longitude: float,
        sun_info: dict
    ) -> None:
    '''
    **Create a polar plot showing the daylight hours for the specified date and location.**

    Uses the ***astral*** library to calculate the sunrise, sunset, and twilight times.

    https://pypi.org/project/astral/

    https://sffjunkie.github.io/astral/

    :param times: A dictionary containing the times of the events shown in the plot (e.g., sunrise, sunset).
    :type times: dict
    :param location: A Location object containing information about the location (name, region, timezone, latitude, longitude).
    :type location: LocationInfo
    :param target_date: The date for which the plot is generated.
    :type target_date: datetime
    :param my_latitude: The latitude of the location (°).
    :type my_latitude: float
    :param my_longitude: The longitude of the location (°).
    :type my_longitude: float
    :param sun_info: A dictionary containing information about the sun events (e.g., sunrise, sunset, dawn, dusk).
    :type sun_info: dict
    '''
    
    # Create polar plot
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={'projection': 'polar'})
    ax = cast(PolarAxes, ax)  # Tell Pylance that ax is a PolarAxes
    ax.set_theta_zero_location('N')  # Midnight at top
    ax.set_theta_direction(-1)  # Clockwise rotation

    # Full circle for reference
    full_circle = 2 * np.pi

    angles = {k: time_to_angle(v) for k, v in times.items()}

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
    ax.set_xticklabels(hour_labels, fontsize=8)

    ax.set_yticks([])  # Remove radial ticks
    ax.set_yticklabels([])  # Remove radial labels
    ax.yaxis.grid(False)  # Remove radial grid lines
    ax.xaxis.grid(False)

    r_values = [1, 1.05]  # Slightly outside the filled area
    for angle in np.linspace(0, 2*np.pi, 24, endpoint=False):
        ax.plot([angle, angle], r_values, color='black', linewidth=0.8, linestyle='solid')

    # Draw the outer circle at r = 1.05
    outer_circle = np.linspace(0, full_circle, 100)
    ax.plot(outer_circle, np.full_like(outer_circle, 1.05), color='black', linewidth=1.2)

    # Title
    title_str = location.name[:15] + '...' if len(location.name) > 15 else location.name
    date_str = target_date.strftime("%Y-%m-%d")  # Format: YYYY-MM-DD
    plt.title(f"{title_str} ({my_latitude:.3f}, {my_longitude:.3f}): {date_str}", pad=35, fontsize=16)

    # Display length of the day
    day_length = sun_info['sunset'] - sun_info['sunrise']
    day_length_str = str(day_length).split('.')[0]

    # Display sunrise and sunset times
    sunrise_time_str = sun_info['sunrise'].strftime("%H:%M")
    sunset_time_str = sun_info['sunset'].strftime("%H:%M")

    # Add text annotations for sunrise and sunset
    plt.figtext(0.5, 0.01, f"Sunrise: {sunrise_time_str}    Sunset: {sunset_time_str}    Length of Day: {day_length_str}", ha='center', fontsize=12)

    plt.show()

def main() -> None:
    '''
    **Main function for creating the daylight hours plot.**
    '''

    # Get target date from user
    user_input = input("Enter the target date (YYYY-MM-DD) or press Enter to use the current date: ").strip()
    # Use today's date if input is empty
    if user_input:
        try:
            target_date = datetime.strptime(user_input, "%Y-%m-%d")
        except ValueError:
            print("Invalid format! Using today's date instead.")
            target_date = datetime.today()
    else:
        target_date = datetime.today()

    # Define twilight depression (angle below horizon for dawn/dusk calculation)
    twilight_depression = 6  # 6° = civil twilight

    # List available timezones
    # from astral import zoneinfo
    # print(zoneinfo.available_timezones())

    # Define location
    my_latitude: float = 42.22530
    my_longitude: float = -83.74567
    my_location_name: str = "Ann Arbor"
    my_region: str = "Michigan/USA"
    my_tz: str = "US/Eastern"

    # Create a location object
    location = LocationInfo(
        my_location_name, 
        my_region, 
        my_tz, 
        my_latitude, 
        my_longitude
    )

    # Get timezone
    tz = pytz.timezone(location.timezone)  # pytz timezone object - see https://pypi.org/project/pytz/

    # Get sunrise, sunset, and twilight times
    try:
        sun_info: dict = sun(location.observer, date=target_date, tzinfo=tz, dawn_dusk_depression=twilight_depression)
    except ValueError as e:
        print(f"ValueError: {e}")
        return  # Exit the function
    except Exception as e:
        print(f"Error: {e}")
        return  # Exit the function
    
    # Extract event times
    times: dict = {
        "midnight": datetime.strptime("00:00", "%H:%M").time(),
        "noon": datetime.strptime("12:00", "%H:%M").time(),
        "sunrise": sun_info['sunrise'].time(),
        "sunset": sun_info['sunset'].time(),
        "first_light": sun_info['dawn'].time(),
        "last_light": sun_info['dusk'].time()
    }

    # Print information
    print(f"Location: {location.name}")
    print(f"TZ: {tz}")
    print(f"Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"Sunrise: {sun_info['sunrise']}, Sunset: {sun_info['sunset']}")
    print(f"Daylight hours: {sun_info['sunset'] - sun_info['sunrise']}")   
    print(f"Dawn: {sun_info['dawn']}, Dusk: {sun_info['dusk']} (Twilight depression = {twilight_depression}°)")

    # Create the plot
    _create_plot(times, location, target_date, my_latitude, my_longitude, sun_info)


if __name__ == "__main__":
    main()
