import threading
import time
import random
import logging
from pathlib import Path
import sys

# Aggiungi la root al path per importare core_logic
sys.path.append(str(Path(__file__).parent.parent))
from core_logic import safe_save_json, safe_load_json, CONFIG_DIR

TEST_FILE = CONFIG_DIR / "concurrency_test.json"
ITERATIONS = 50
THREADS = 20

logging.basicConfig(level=logging.INFO, format="%(message)s")

def writer(id):
    for i in range(ITERATIONS):
        data = safe_load_json(TEST_FILE)
        data[f"thread_{id}"] = i
        safe_save_json(TEST_FILE, data)
        time.sleep(random.random() * 0.01)

def reader(id):
    errors = 0
    for i in range(ITERATIONS):
        data = safe_load_json(TEST_FILE)
        if not isinstance(data, dict):
            logging.error(f"Reader {id}: Data corrupted or empty!")
            errors += 1
        time.sleep(random.random() * 0.01)
    if errors > 0:
        logging.error(f"Reader {id} finished with {errors} errors.")

def run_test():
    logging.info(f"Starting concurrency test on {TEST_FILE}...")
    safe_save_json(TEST_FILE, {}) # Init

    threads = []
    # Mix writers and readers
    for i in range(10):
        t = threading.Thread(target=writer, args=(i,))
        threads.append(t)
        t.start()
    
    for i in range(10):
        t = threading.Thread(target=reader, args=(i+10,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    final_data = safe_load_json(TEST_FILE)
    logging.info(f"Test completed. Final keys count: {len(final_data)} (Expected ~10)")
    logging.info("If you see no 'JSONDecodeError' or 'Data corrupted' logs above, the fix is working.")

if __name__ == "__main__":
    run_test()
