import time
from utils import write_data
from argparse import ArgumentParser
from datetime import datetime
from sniff import sniff_packets
import sys

SCAN_DURATION = 300
MAX_LENGTH = 49_000

def dummy_data() -> dict[str, int]:
    import random
    abc = "abcdefghijklmnopqrstuvwxyz"
    def random_string(length=5):
        return ''.join(random.choices(abc, k=length))

    return {random_string(length=6) : -10 for _ in range(10000)}

def get_crowd_data(scan_duration : int) -> dict[str, int]:
    interface = 'alfa' 
    return sniff_packets(interface, scan_duration) 
    # return dummy_data()

def split_dict_by_max_length(input_dict : dict, max_length : int) -> list[dict]:
    result = []
    current_chunk = {}
    
    for key, value in input_dict.items():
        temp_chunk = current_chunk.copy()
        temp_chunk[key] = value
        if len(str(temp_chunk)) > max_length:
            result.append(current_chunk)
            current_chunk = {key: value}
        else:
            current_chunk = temp_chunk
    
    if current_chunk:
        result.append(current_chunk)
        
    result = [str(chunk) for chunk in result]
    
    return result   

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
        
    print("Dummy trial successful, starting main loop...", flush=True)
        
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
        
        # this is a list of strings to be logged
        crowd_data = split_dict_by_max_length(crowd_data, MAX_LENGTH)
        
        data = [
            {
            "device_name": device_name,
            "timestamp": timestamp,
            "crowd_data": d,
            } 
            for d in crowd_data
            ]
        
        try:
            write_data(data)
        except Exception as e:
            print(f"Error writing data: {e}", flush=True)
            sys.exit(1)
        
        print(f"Data written at {timestamp} with lengths:", flush=True)
        for d in crowd_data:
            print(f"  {len(d)} characters", flush=True)
            
        exit()
        
if __name__ == "__main__":
    main()
        