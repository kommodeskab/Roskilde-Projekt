import time
from utils import write_data
from argparse import ArgumentParser
from datetime import datetime
from sniff import sniff_packets
import sys

def get_crowd_data() -> dict[str, int]:
    interface = 'alfa' 
    scan_duration = 60 
    return sniff_packets(interface, scan_duration)    

def main():
    parser = ArgumentParser()
    parser.add_argument("--device_name", type=str, required=True)
    
    args = parser.parse_args()
    device_name : str = args.device_name
    
    now = datetime.now()
    print(f"Waiting {60 - now.second} seconds until the next minute begins...", flush=True)
    time.sleep(60 - now.second)
        
    while True:
        try:
            crowd_data = get_crowd_data()
            
        except OSError as e:
            print(f"Error sniffing packets: {e}", flush=True)
            sys.exit(1)
            
        except Exception as e:
            print(f"Unexpected error: {e}", flush=True)
            sys.exit(1)
            
        if len(crowd_data) == 0:
            # if no data is found, it is most likely because the interface is not in monitor mode
            # exiting the script allows the raspberry to set the interface to monitor mode again
            print("No data found, trying a restart...", flush=True)
            sys.exit(1)
        
        # format the timestamp as 'YYYY-MM-DD HH:MM'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        data = {
            "device_name": device_name,
            "timestamp": timestamp,
            "crowd_data": str(crowd_data)
        }
        
        try:
            write_data(data)
        except Exception as e:
            print(f"Error writing data: {e}", flush=True)
            sys.exit(1)
        
        print(f"Data written at {timestamp}: {crowd_data}", flush=True)
        
if __name__ == "__main__":
    main()
        