from datetime import datetime
import time
import subprocess

def run_at_midnight():
    now = datetime.now()
    tomorrow = now.day + 1
    midnight = datetime.now().replace(day=tomorrow, hour=0, minute=0,second=0, microsecond=0)
    
    print(f"scheduled to run catdroool shipping report at {midnight}")

    while datetime.now() < midnight:
        time.sleep(15)
    
    subprocess.run(['bash', 'scripts/catdroool-startup'])

if __name__ == "__main__":
    run_at_midnight()
    print("Catdroool started")

