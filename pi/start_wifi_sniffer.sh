#!/bin/bash

PYTHON_DEVICE_NAME="census1"


LOG_FILE="/var/log/wifi_sniffer_startup.log"

echo "$(date): Starting Wi-Fi sniffer setup..." >> "$LOG_FILE"

PROJECT_DIR="/home/$PYTHON_DEVICE_NAME/Roskilde-Projekt/"
echo "$(date): Project directory set to $PROJECT_DIR." >> "$LOG_FILE"

ip link set wlan1 down >> "$LOG_FILE" 2>&1
echo "$(date): wlan1 is down." >> "$LOG_FILE"

iw dev wlan1 set type monitor >> "$LOG_FILE" 2>&1
echo "$(date): wlan1 type set to monitor." >> "$LOG_FILE"

ip link set wlan1 up >> "$LOG_FILE" 2>&1
echo "$(date): wlan1 is up in monitor mode." >> "$LOG_FILE"

cd "$PROJECT_DIR" >> "$LOG_FILE" 2>&1
echo "$(date): Changed directory to $PROJECT_DIR." >> "$LOG_FILE"

VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
echo "$(date): Found virtual environment Python: $VENV_PYTHON" >> "$LOG_FILE"

"$VENV_PYTHON" raspberry.py --device_name="$PYTHON_DEVICE_NAME" >> "$LOG_FILE" 2>&1
echo "$(date): Python script terminated." >> "$LOG_FILE"

exit $?