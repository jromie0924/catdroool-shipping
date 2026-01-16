import subprocess
from datetime import datetime
import time
import os

startup_time = datetime.now().strftime("%Y-%m-%d %H:%M%S")
print(f"Startup script initiated; timestamp: {startup_time}")

is_midnight = False

while not is_midnight:
  # Check if current time is midnight
  now = datetime.now()
  is_midnight = now.hour == 0 and now.minute == 0
  time.sleep(30)

script_dir = os.path.dirname(os.path.abspath(__file__))

subprocess.run([f'{script_dir}/catdroool-startup'], capture_output=True, text=True)
