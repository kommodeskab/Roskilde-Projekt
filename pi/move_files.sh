sudo cp pi/start_wifi_sniffer.sh /usr/local/bin/start_wifi_sniffer.sh
sudo chmod +x /usr/local/bin/start_wifi_sniffer.sh

sudo cp pi/wifi-sniffer.service /etc/systemmd/system/wifi-sniffer.service

# remember to change the path (census1) to the correct path

# activate the service
sudo systemctl daemon-reload
sudo systemctl enable wifi-sniffer.service
sudo systemctl start wifi-sniffer.service

# and check the status
systemctl status wifi-sniffer.service
journalctl -u wifi-sniffer.service -f

# the reboot to check if it works
reboot

# and check the log file
sudo tail -f /var/log/wifi_sniffer_startup.log