import hashlib
from scapy.all import sniff, Dot11
from scapy.packet import Packet
from functools import partial

def hash_mac(mac : str) -> str:    
    hashed = hashlib.sha256(mac.encode()).hexdigest()
    # cap the hash at 6 characters
    hashed = hashed[:6]
    
    return hashed

def packet_handler(pkt : Packet, device_rssi : dict) -> None:
    if pkt.haslayer(Dot11) and pkt.type == 0:  # management frame
        mac = pkt.addr2
        if mac:
            mac_hash = hash_mac(mac)

            try:
                rssi = pkt.dBm_AntSignal
            except:
                rssi = None

            if rssi is not None:
                device_rssi[mac_hash] = rssi
            
def sniff_packets(interface : str, duration : int):
    device_rssi = {}
    prn = partial(packet_handler, device_rssi=device_rssi)
    sniff(iface=interface, prn=prn, timeout=duration, store=0)
    return device_rssi

