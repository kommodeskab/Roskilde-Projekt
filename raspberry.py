import time
from utils import write_data
from argparse import ArgumentParser
from datetime import datetime
from sniff import sniff_packets

def get_crowd_data() -> dict[str, int]:
    interface = 'wlan1' 
    scan_duration = 50
    return sniff_packets(interface, scan_duration)    

def main():
    parser = ArgumentParser()
    parser.add_argument("--device_name", type=str, required=True)
    
    args = parser.parse_args()
    device_name : str = args.device_name
    
    now = datetime.now()
    print(f"Waiting {60 - now.second} seconds until the next minute begins...")
    time.sleep(60 - now.second)
        
    while True:
        crowd_data = get_crowd_data()
        # format the timestamp as 'YYYY-MM-DD HH:MM'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        data = {
            "device_name": device_name,
            "timestamp": timestamp,
            "crowd_data": str(crowd_data)
        }
        write_data(data)
        print(f"Data written at {timestamp}: {crowd_data}")
        time.sleep(60)
        
if __name__ == "__main__":
    main()
        