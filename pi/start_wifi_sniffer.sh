#!/bin/bash

# Log file for debugging
LOG_FILE="/var/log/wifi_sniffer_startup.log"

echo "$(date): Starting Wi-Fi sniffer setup..." >> "$LOG_FILE"

# 1. Take down the interface
ip link set wlan1 down >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "$(date): Error bringing wlan1 down. Exiting." >> "$LOG_FILE"
    exit 1
fi
echo "$(date): wlan1 is down." >> "$LOG_FILE"

# 2. Set interface to monitor mode
iw dev wlan1 set type monitor >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "$(date): Error setting wlan1 to monitor mode. Exiting." >> "$LOG_FILE"
    exit 1
fi
echo "$(date): wlan1 type set to monitor." >> "$LOG_FILE"

# 3. Bring the interface up in monitor mode
ip link set wlan1 up >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "$(date): Error bringing wlan1 up in monitor mode. Exiting." >> "$LOG_FILE"
    exit 1
fi
echo "$(date): wlan1 is up in monitor mode." >> "$LOG_FILE"

# 4. Navigate to your project directory
# IMPORTANT: Use the absolute path to your project directory.
# Replace `/home/yourusername/Roskilde-Projekt/` with the actual path.
PYTHON_SCRIPT_USER=$(whoami) # This will be 'root' if User= is not specified in .service file
echio "$(date): Current user is $PYTHON_SCRIPT_USER." >> "$LOG_FILE"

PROJECT_DIR="/home/$PYTHON_SCRIPT_USER/Roskilde-Projekt/" # Assuming Raspberry Pi and your home dir
cd "$PROJECT_DIR" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "$(date): Error changing directory to $PROJECT_DIR. Exiting." >> "$LOG_FILE"
    exit 1
fi
echo "$(date): Changed directory to $PROJECT_DIR." >> "$LOG_FILE"

# 5. Activate the virtual environment
# Note: When sourcing a script like 'activate' from a non-interactive shell,
# it might not behave exactly as in a terminal.
# It's better to explicitly use the Python interpreter from the venv.
# This assumes your virtual environment is inside Roskilde-Projekt/.venv/
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "$(date): Virtual environment Python interpreter not found at $VENV_PYTHON. Exiting." >> "$LOG_FILE"
    exit 1
fi
echo "$(date): Found virtual environment Python: $VENV_PYTHON" >> "$LOG_FILE"

# 6. Run the Python script
# Using $(whoami) might not work as expected in a systemd service,
# as the user might be root. Better to hardcode if it's always "pi" or similar,
# or define it in the service file via `User=`.
# Let's assume you want it to run as the user who owns the script for now.
# Replace 'yourusername' if 'pi' is not correct.
# Alternatively, if you know the user, hardcode: PYTHON_SCRIPT_USER="pi"

echo "$(date): Running Python script as user: $PYTHON_SCRIPT_USER" >> "$LOG_FILE"

# Execute the python script using the virtual environment's python
# Note: No `sudo` needed here if the systemd service is already running as root or a privileged user.
# If you want it to run as a specific non-root user, you'd set `User=youruser` in the .service file
# and then remove the `sudo` from this line.
"$VENV_PYTHON" raspberry.py --device_name="$PYTHON_SCRIPT_USER" >> "$LOG_FILE" 2>&1 & # Run in background if it's a long-running process
echo "$(date): Python script started." >> "$LOG_FILE"

exit 0