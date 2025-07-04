from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import gspread
from gspread import Worksheet
from oauth2client.service_account import ServiceAccountCredentials
import math

COLUMNS = ["device_name", "timestamp", "crowd_data"]
SHEET_NAME = "data" #"data" #"synthetic_data"
DEVICE_POSITIONS = {
    "census1": (55.84697864064483, 12.527829569730192),
    "census2": (55.84698202870734, 12.527924788142869),
    "census3": (55.84698729902622, 12.528038111464998)
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


def ll_to_xy(lat: float, lon: float, origin_lat: float, origin_lon: float) -> tuple[float, float]:
    """Approx. equirectangular projection, metres east/north of a dynamic origin."""
    # Calculate cosine of the origin latitude inside the function
    cos_lat0 = math.cos(math.radians(origin_lat))
    
    # Calculate distance based on the provided origin
    dx = _EARTH_R * math.radians(lon - origin_lon) * cos_lat0
    dy = _EARTH_R * math.radians(lat - origin_lat)
    return dx, dy


def xy_to_ll(x: float, y: float, origin_lat: float, origin_lon: float) -> tuple[float, float]:
    """Inverse of the dynamic `ll_to_xy`."""
    # Calculate cosine of the origin latitude inside the function
    cos_lat0 = math.cos(math.radians(origin_lat))
    
    # Calculate lat/lon based on the provided origin
    lat = origin_lat + (y / _EARTH_R) * (180 / math.pi)
    lon = origin_lon + (x / (_EARTH_R * cos_lat0)) * (180 / math.pi)
    return lat, lon





def rssi_to_distance(rssi : float, N : float, measured_power : float) -> float:
    # rssi = Received Signal Strength Indicator
    # N = device constat, usually between 2 and 4, 2 for free space, 3 for urban areas, 4 for indoor
    # measured_power = RSSI at 1 meter distance, needs to be calibrated for each device, around -16
    return 10 ** ((measured_power - rssi) / (10 * N))
