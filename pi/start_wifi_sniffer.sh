#!/bin/bash

PYTHON_DEVICE_NAME="census1"


LOG_FILE="/var/log/wifi_sniffer_startup.log"

echo "$(date): Starting Wi-Fi sniffer setup..." >> "$LOG_FILE"

PROJECT_DIR="/home/$PYTHON_DEVICE_NAME/Roskilde-Projekt/"
echo "$(date): Project directory set to $PROJECT_DIR." >> "$LOG_FILE"

# check and try 5 times with 5 seconds interval if the wlan1 interface is up
for i in {1..5}; do
    ip link set wlan1 down >> "$LOG_FILE" 2>&1
    iw dev wlan1 set type monitor >> "$LOG_FILE" 2>&1
    ip link set wlan1 up >> "$LOG_FILE" 2>&1
    if iw dev wlan1 info | grep -q "type monitor"; then
        echo "$(date): wlan1 is successfully set to monitor mode." >> "$LOG_FILE"
        break
    else
        echo "$(date): Attempt $i: wlan1 is not in monitor mode, retrying in 5 seconds..." >> "$LOG_FILE"
        sleep 5
    fi
done

if ! iw dev wlan1 info | grep -q "type monitor"; then
    echo "$(date): Failed to set wlan1 to monitor mode after 5 attempts." >> "$LOG_FILE"
    exit 1
fi

cd "$PROJECT_DIR" >> "$LOG_FILE" 2>&1
echo "$(date): Changed directory to $PROJECT_DIR." >> "$LOG_FILE"

VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
echo "$(date): Found virtual environment Python: $VENV_PYTHON" >> "$LOG_FILE"

"$VENV_PYTHON" raspberry.py --device_name="$PYTHON_DEVICE_NAME" >> "$LOG_FILE" 2>&1
echo "$(date): Python script terminated." >> "$LOG_FILE"

exit $?