import subprocess
import sys
import time
import logging
from datetime import datetime

# Configurable settings
SLEEP_INTERVAL = 600  # seconds (10 minutes)
MAX_RETRIES = 5
RETRY_BACKOFF = 60  # seconds

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

def run_pipeline():
    logging.info('Starting news pipeline update...')
    try:
        result = subprocess.run([sys.executable, 'update_content.py'], capture_output=True, text=True)
        logging.info(result.stdout)
        if result.returncode != 0:
            logging.error(f"Pipeline failed: {result.stderr}")
            return False
        logging.info('Pipeline completed successfully.')
        return True
    except Exception as e:
        logging.error(f"Exception running pipeline: {e}")
        return False

def main():
    consecutive_failures = 0
    while True:
        success = run_pipeline()
        if not success:
            consecutive_failures += 1
            if consecutive_failures >= MAX_RETRIES:
                logging.error(f"Pipeline failed {MAX_RETRIES} times in a row. Backing off for {RETRY_BACKOFF} seconds.")
                time.sleep(RETRY_BACKOFF)
                consecutive_failures = 0
            else:
                logging.info(f"Retrying in {RETRY_BACKOFF} seconds...")
                time.sleep(RETRY_BACKOFF)
        else:
            consecutive_failures = 0
            logging.info(f"Sleeping for {SLEEP_INTERVAL} seconds before next run...")
            time.sleep(SLEEP_INTERVAL)

if __name__ == "__main__":
    main()
