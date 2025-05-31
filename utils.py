from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import gspread
from gspread import Worksheet
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

COLUMNS = ["device_name", "location", "timestamp", "crowd_count"]
SHEET_NAME = "data"

def scrape_schedule() -> list:
    """
    Scrapes the schedule for the festival and returns it as a dictionary.
    The schedule is a list of dictionaries, each containing the title, time, and location of an event.
    """
    schedule = []

    weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    first_date = datetime(2025, 6, 29)

    for i, day in enumerate(weekdays):
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
            
            event_time = first_date + timedelta(days=i, hours=hour, minutes=minute)
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

def read_data() -> pd.DataFrame:
    sheet = get_sheet()
    data = sheet.get_all_records()
    df = pd.DataFrame(data[1:], columns=data[0])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def write_data(data : dict) -> None:
    assert isinstance(data, dict), "Data must be a dictionary"
    assert len(data) == len(COLUMNS), "Data length must match number of columns"
    assert all(key in COLUMNS for key in data.keys()), "Data keys must match column names"
    
    sheet = get_sheet()
    header = sheet.row_values(1)
    
    if len(header) == 0:
        sheet.append_row(COLUMNS)
    elif header != COLUMNS:
        raise ValueError(f"Header mismatch: {header} != {COLUMNS}")
        
    data = [data[column] for column in COLUMNS]
    sheet.append_row(data)
    
if __name__ == "__main__":
    write_data({
        "device_name": "Test Device",
        "location": "Test Location",
        "timestamp": datetime.now().isoformat(),
        "crowd_count": 100
    })