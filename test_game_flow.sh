#!/bin/bash

# Check for virtual environment
if [ -d "venv" ]; then
  echo "Activating virtual environment."
  source venv/bin/activate
else
  echo "Virtual environment 'venv' not found. Please create it."
  # Optionally, exit here if the venv is strictly required
  # exit 1
fi

# Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Run unit tests
echo "Running unit tests..."
python -m unittest tests/test_game_logic.py
TEST_STATUS=$?

# Exit with the status of the test command
exit $TEST_STATUS
