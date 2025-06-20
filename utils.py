from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import gspread
from gspread import Worksheet
from oauth2client.service_account import ServiceAccountCredentials
import numpy as np

COLUMNS = ["device_name", "timestamp", "crowd_data"]
SHEET_NAME = "data"
DEVICE_POSITIONS = {
    "device1": (1, 1),
    "device2": (1, -1),
    "device3": (-1, 1)
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
    
def triangulate_positions(D, x1, x2, x3):
    """
    Fast, vectorized triangulation from distances to 3 known devices.
    
    Parameters:
    - D: (N, 3) array of distances from each point to the 3 devices
    - x1, x2, x3: tuples or arrays with (x, y) positions of the 3 devices

    Returns:
    - positions: (N, 2) array of estimated (x, y) positions
    """
    
    # D can contain NaNs. We handle them by substituting them with the largest number in that column
    max_distances = np.nanmax(D, axis=0)
    D = np.where(np.isnan(D), max_distances, D) 
    
    p1 = np.array(x1)
    p2 = np.array(x2)
    p3 = np.array(x3)

    # Differences in coordinates
    ex = p2 - p1  # (2,)
    ey = p3 - p1  # (2,)

    # Coefficient matrix A (2x2)
    A = np.vstack([ex, ey])  # (2, 2)

    # Precompute squared distances
    d1_sq = D[:, 0] ** 2
    d2_sq = D[:, 1] ** 2
    d3_sq = D[:, 2] ** 2

    # Precompute constants
    p1_sq = np.dot(p1, p1)
    p2_sq = np.dot(p2, p2)
    p3_sq = np.dot(p3, p3)

    b1 = 0.5 * (d1_sq - d2_sq + p2_sq - p1_sq)
    b2 = 0.5 * (d1_sq - d3_sq + p3_sq - p1_sq)
    B = np.stack([b1, b2], axis=1)  # (N, 2)

    # Solve for positions
    A_inv = np.linalg.pinv(A)  # (2, 2)
    positions = B @ A_inv.T  # (N, 2)

    return positions