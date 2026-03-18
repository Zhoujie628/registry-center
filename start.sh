#!/bin/bash

# Get the absolute path of the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET_DIR="${SCRIPT_DIR}/agent_registry"

if [ -d "$TARGET_DIR" ]; then
    TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
else
    echo "Error: Target directory does not exist: $TARGET_DIR"
    exit 1
fi

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  ===== Security Warning ====="
    echo "You are currently running as root!"
    echo "Executing commands as root may pose security risks. Please proceed with caution."
    echo "   It is recommended to use root privileges only when necessary."
    echo "============================="
fi

# Change to target directory
cd "$TARGET_DIR" || {
    echo "Error: Cannot enter directory $TARGET_DIR"
    exit 1
}

PYTHON_SCRIPT="start.py"

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script $PYTHON_SCRIPT does not exist in $TARGET_DIR"
    exit 1
fi

# Start the Python script
echo "Starting Python script: $PYTHON_SCRIPT"
python "$PYTHON_SCRIPT"


exit 0