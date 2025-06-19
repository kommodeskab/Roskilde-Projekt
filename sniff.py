import hashlib
from scapy.all import sniff, Dot11
from collections import defaultdict

# Set your interface and scan duration
INTERFACE = 'wlan0mon'
SCAN_DURATION = 10  # seconds

# Dictionary to store strongest RSSI for each device (or "None")
device_rssi = {}

def hash_mac(mac):
    """Hash a MAC address using SHA-256 and return as hex string"""
    return hashlib.sha256(mac.encode()).hexdigest()

def packet_handler(pkt):
    if pkt.haslayer(Dot11) and pkt.type in [0]:  # management frame
        mac = pkt.addr2
        if mac:
            mac_hash = hash_mac(mac)

            try:
                rssi = pkt.dBm_AntSignal
            except:
                rssi = None

            device_rssi[mac_hash] = rssi if rssi is not None else "None"

print(f"Sniffing on {INTERFACE} for {SCAN_DURATION} seconds...")
sniff(iface=INTERFACE, prn=packet_handler, timeout=SCAN_DURATION, store=0)

print("\nDetected devices (hashed MAC -> RSSI):")
print(device_rssi)