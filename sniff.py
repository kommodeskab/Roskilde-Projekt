from scapy.all import sniff, Dot11

# Set of detected MAC addresses to avoid duplicates
devices = set()

def packet_handler(pkt):
    # Check if it's a management frame and a beacon or probe request
    if pkt.haslayer(Dot11):
        mac = pkt.addr2
        if mac and mac not in devices:
            devices.add(mac)
            print(f"Detected device: {mac}")

# Replace 'wlan0mon' with your actual monitor-mode interface
sniff(iface='wlan0mon', prn=packet_handler, store=0)
