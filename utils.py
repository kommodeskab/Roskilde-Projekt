from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import gspread
from gspread import Worksheet
from oauth2client.service_account import ServiceAccountCredentials

COLUMNS = ["device_name", "location", "timestamp", "crowd_count"]
SHEET_NAME = "data"

day_to_datetime = {
    'Sunday':       datetime(2025, 6, 29),
    'Monday':       datetime(2025, 6, 30),
    'Tuesday':      datetime(2025, 7, 1),
    'Wednesday':    datetime(2025, 7, 2),
    'Thursday':     datetime(2025, 7, 3),
    'Friday':       datetime(2025, 7, 4),
    'Saturday':     datetime(2025, 7, 5)
}

def scrape_schedule() -> list:
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

def read_data():
    import pandas as pd
    sheet = get_sheet()
    data = sheet.get_all_records()
    if not data:
        # returns an empty DataFrame
        return pd.DataFrame(columns=COLUMNS)
    df = pd.DataFrame(data, columns=COLUMNS)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='timestamp').reset_index(drop=True)
    return df

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
    
if __name__ == "__main__":
    write_data([{
        "device_name": "Test Device",
        "location": "Test Location",
        "timestamp": datetime.now().isoformat(),
        "crowd_count": 100
    }])