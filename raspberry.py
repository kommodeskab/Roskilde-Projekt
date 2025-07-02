import time
from utils import write_data
from argparse import ArgumentParser
from datetime import datetime
from sniff import sniff_packets
import sys

SCAN_DURATION = 300

def get_crowd_data(scan_duration : int) -> dict[str, int]:
    interface = 'alfa' 
    return sniff_packets(interface, scan_duration)    

def main():
    parser = ArgumentParser()
    parser.add_argument("--device_name", type=str, required=True)
    
    args = parser.parse_args()
    device_name : str = args.device_name
    
    # start by sniffing for 30 seconds
    # if no devies are picked up, we exit the script
    dummy_data = get_crowd_data(30)
    if len(dummy_data) == 0:
        print("No data found during dummy trial, restarting...", flush=True)
        sys.exit(1)
        
    while True:
        try:
            crowd_data = get_crowd_data(SCAN_DURATION)
                    
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
        