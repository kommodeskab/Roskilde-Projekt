#!/bin/bash

PYTHON_DEVICE_NAME="census1"


LOG_FILE="/var/log/wifi_sniffer_startup.log"

echo "$(date): Starting Wi-Fi sniffer setup..." >> "$LOG_FILE"

PROJECT_DIR="/home/$PYTHON_DEVICE_NAME/Roskilde-Projekt/"
echo "$(date): Project directory set to $PROJECT_DIR." >> "$LOG_FILE"

# try to put wlan1 into monitor mode
ip link set wlan1 down >> "$LOG_FILE" 2>&1
iw dev wlan1 set type monitor >> "$LOG_FILE" 2>&1
ip link set wlan1 up >> "$LOG_FILE" 2>&1

# Check if wlan1 is in monitor mode
# if not, exit with an error
# the .service file will make sure that this script is run again if it fails
if ! iw dev wlan1 info | grep -q "type monitor"; then
    echo "$(date): Failed to set wlan1 to monitor mode." >> "$LOG_FILE"
    exit 1
fi

echo "$(date): Successfully set wlan1 to monitor mode." >> "$LOG_FILE"

cd "$PROJECT_DIR" >> "$LOG_FILE" 2>&1
echo "$(date): Changed directory to $PROJECT_DIR." >> "$LOG_FILE"

VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
echo "$(date): Found virtual environment Python: $VENV_PYTHON" >> "$LOG_FILE"

"$VENV_PYTHON" raspberry.py --device_name="$PYTHON_DEVICE_NAME" >> "$LOG_FILE" 2>&1
echo "$(date): Python script terminated." >> "$LOG_FILE"

# if the script fails, exit with an error and restart the service
echo "$(date): The python script has exited for some reason (see log). Restarting the service..." >> "$LOG_FILE"
exit 1