import blessed
import time

term = blessed.Terminal()

print("Line 1: Standard output before blessed.")

# Try to print at the bottom of the terminal
# (or top, if height is small, to ensure visibility)
status_line_y = term.height - 1
if status_line_y < 0: # term.height might be None or 0 if not a full terminal
    status_line_y = 0

# Ensure x-coordinate is within width if possible, else 0
status_line_x = 0
if term.width is not None and 0 >= term.width:
    status_line_x = term.width -1 if term.width > 0 else 0


try:
    with term.location(status_line_x, status_line_y):
        print(f"Status: Time | State (at y={status_line_y})")
except Exception as e:
    print(f"Error using term.location: {e}")
    # Fallback if term.location fails, just print normally
    print("Status: Time | State (fallback, not positioned)")

print("Line 2: More standard output after blessed output.")
print("Line 3: Checking if status line persists.")
print(f"Terminal height: {term.height}, width: {term.width}")
print("Test complete. Observe if the 'Status:' line remained fixed.")
