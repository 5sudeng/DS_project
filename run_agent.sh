#!/bin/bash
# Wrapper script to run the interactive shopping agent with the correct conda environment python

# Absolute path to the conda environment python
PYTHON_EXEC="/opt/homebrew/Caskroom/miniforge/base/envs/shopping_env/bin/python"

if [ ! -f "$PYTHON_EXEC" ]; then
    echo "Error: Python executable not found at $PYTHON_EXEC"
    echo "Please ensure the 'shopping_env' conda environment is created."
    exit 1
fi

echo "Using Python: $PYTHON_EXEC"
"$PYTHON_EXEC" main.py --cookie-file=cookie.txt --input-mode text --output-mode text "$@"
