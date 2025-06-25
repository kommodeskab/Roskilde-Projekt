from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import gspread
from gspread import Worksheet
from oauth2client.service_account import ServiceAccountCredentials
import math

COLUMNS = ["device_name", "timestamp", "crowd_data"]
SHEET_NAME = "synthetic_data" #"data" #"synthetic_data"
DEVICE_POSITIONS = {
    "census1": (55.631111, 12.124757),
    "census2": (55.630866, 12.125152),
    "census3": (55.631235, 12.125442)
}


day_to_datetime = {
    'Sunday':       datetime(2025, 6, 29),
    'Monday':       datetime(2025, 6, 30),
    'Tuesday':      datetime(2025, 7, 1),
    'Wednesday':    datetime(2025, 7, 2),
    'Thursday':     datetime(2025, 7, 3),
    'Friday':       datetime(2025, 7, 4),
    'Saturday':     datetime(2025, 7, 5)
}

def scrape_schedule() -> list[dict]:
    """
    Scrapes the schedule for the festival and returns it as a dictionary.
    The schedule is a list of dictionaries, each containing the title, time, and location of an event.
    """
    schedule = []

    for day in day_to_datetime.keys():
        url = f"https://www.roskilde-festival.dk/en/lineup/schedule?filter={day}"
        response = requests.get(url)
            
        soup = BeautifulSoup(response.content, 'html.parser')
        class_name = "schedule-item_component__3xy_9"
        time_slots = soup.find_all('a', class_=class_name)

        # each timeslot have the following:
        # <h2 class="typography_component__Z0rR8 typography_headlineXSmallHeavy__rAHbS schedule-item_title__Ifafr">Hatha yoga</h2>
        # <p class="typography_component__Z0rR8 typography_bodySmall__p_2To schedule-item_timeSlot__tuJvO">09.00, Stadion</p>
        # extract the title, time and location
        for time_slot in time_slots:
            title = time_slot.find('h2').text.strip()
            time_location = time_slot.find('p').text.strip().split(',')
            time = time_location[0].strip()
            location = time_location[1].strip() if len(time_location) > 1 else "Unknown Location"
            hour, minute = map(int, time.split('.'))
            
            event_time = day_to_datetime[day] + timedelta(hours=hour, minutes=minute)
            event = {
                'title': title,
                'time': event_time,
                'location': location
            }
            schedule.append(event)

    return schedule

def get_sheet() -> Worksheet:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("excel_key.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    return sheet

def write_data(data : dict | list[dict]) -> None:
    if isinstance(data, dict):
        data = [data]
    
    sheet = get_sheet()
    header = sheet.row_values(1)
    
    if len(header) == 0:
        sheet.append_row(COLUMNS)
    elif header != COLUMNS:
        raise ValueError(f"Header mismatch: {header} != {COLUMNS}")
        
    # convert data to a list of lists
    data = [list(item.values()) for item in data]
    sheet.append_rows(data, value_input_option='USER_ENTERED')





_EARTH_R = 6_371_000.0  # mean Earth radius, metres
_ORIGIN_LAT, _ORIGIN_LON = DEVICE_POSITIONS["census1"]
_cos_lat0 = math.cos(math.radians(_ORIGIN_LAT))


def ll_to_xy(lat: float, lon: float) -> tuple[float, float]:
    """Approx. equirectangular projection, metres east/north of origin."""
    dx = _EARTH_R * math.radians(lon - _ORIGIN_LON) * _cos_lat0
    dy = _EARTH_R * math.radians(lat - _ORIGIN_LAT)
    return dx, dy


def xy_to_ll(x: float, y: float) -> tuple[float, float]:
    """Inverse of `ll_to_xy`."""
    lat = _ORIGIN_LAT + (y / _EARTH_R) * (180 / math.pi)
    lon = _ORIGIN_LON + (x / (_EARTH_R * _cos_lat0)) * (180 / math.pi)
    return lat, lon


# Pre-project device sites once – used by the dashboard
DEVICE_POSITIONS_XY = {
    d: ll_to_xy(*ll) for d, ll in DEVICE_POSITIONS.items()
}


def rssi_to_distance(rssi : float, N : float, measured_power : float) -> float:
    # rssi = Received Signal Strength Indicator
    # N = device constat, usually between 2 and 4, 2 for free space, 3 for urban areas, 4 for indoor
    # measured_power = RSSI at 1 meter distance, needs to be calibrated for each device, around -16
    return 10 ** ((measured_power - rssi) / (10 * N))
