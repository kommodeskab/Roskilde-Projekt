import time
from utils import write_data
from argparse import ArgumentParser
from datetime import datetime

def get_crowd_count() -> int:
    # TODO: Replace with actual crowd counting logic
    return 0

def main():
    parser = ArgumentParser()
    parser.add_argument("--device_name", type=str, required=True)
    parser.add_argument("--location", type=str, required=True)
    parser.add_argument("--interval", type=float, default=1, help="Interval in minutes to send data")
    
    args = parser.parse_args()
    device_name : str = args.device_name
    location : str = args.location
    interval : int = float(args.interval)
    
    now = datetime.now()    
    
    while True:
        crowd_count = get_crowd_count()
        timestamp = datetime.now().isoformat()
        data = {
            "device_name": device_name,
            "location": location,
            "timestamp": timestamp,
            "crowd_count": crowd_count
        }
        write_data(data)
        time.sleep(interval * 60)
        
if __name__ == "__main__":
    main()
        