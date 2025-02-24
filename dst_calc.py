'''
Determines if Daylight Savings Time is in effect for a given date.

Uses the US rules, i.e., DST is in effect from the second Sunday of 
March until the first Sunday of November.
'''
from datetime import datetime, timedelta

def main() -> None:

    today = datetime.now()  # check if DST is in effect today
    # today = datetime(2025, 7, 1)  # manually specify the date for testing

    print(dst_in_effect(today.year, today.month, today.day))


def dst_in_effect(year: int, month: int, day: int) -> bool:
    '''
    Determines if DST is in effect in the U.S. for a given date.
    '''
    dst_start = _second_sunday(year, 3)   # Second Sunday of March
    dst_end = _first_sunday(year, 11)     # First Sunday of November
    current_date = datetime(year, month, day)
    
    return dst_start <= current_date < dst_end

def _second_sunday(year: int, month: int) -> datetime:
    '''
    Returns the date of the second Sunday of the given month and year.
    '''
    first_day = datetime(year, month, 1)
    first_sunday = first_day + timedelta(days=(6 - first_day.weekday()) % 7)

    return first_sunday + timedelta(weeks=1)

def _first_sunday(year: int, month: int) -> datetime:
    '''
    Returns the date of the first Sunday of the given month and year.
    '''
    first_day = datetime(year, month, 1)

    return first_day + timedelta(days=(6 - first_day.weekday()) % 7)

if __name__ == "__main__":
    main()