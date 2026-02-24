
import os
import sys
import shutil
import time
from pymongo import MongoClient
import threading
import queue

# Adjust path to import core.workers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.workers import worker_export_task

URI = "mongodb://localhost:27017"
DB_NAME = "test_export_safety"
COLL_NAME = "large_dummy"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output_safety_test_large")

def setup_db():
    client = MongoClient(URI)
    db = client[DB_NAME]
    db[COLL_NAME].drop()
    
    # Create 1200 items to force 3 batches (500, 500, 200)
    data = [{"item": f"Item {i}", "price": i} for i in range(1200)]
    db[COLL_NAME].insert_many(data)
    client.close()

def run_export_test():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    q = queue.Queue()
    
    print("Testing PostgreSQL Export with 1200 items...")
    worker_export_task(URI + "/" + DB_NAME, OUTPUT_DIR, "postgresql", False, False, [COLL_NAME], q)
    
    pg_path = os.path.join(OUTPUT_DIR, f"{COLL_NAME}.sql")
    if not os.path.exists(pg_path):
        print("FAILED: Output file not found.")
        return

    with open(pg_path, "r", encoding="utf-8") as f:
        content = f.read()
        
        # Check for multiple INSERT statements
        insert_count = content.count("INSERT INTO")
        # Should detect:
        # 1. First INSERT (written before loop)
        # 2. End of Batch 1 (500) -> Loop writes next INSERT header
        # 3. End of Batch 2 (500) -> Loop writes next INSERT header
        # Total: 3 INSERT statements
        
        print(f"Found {insert_count} INSERT statements.")
        
        if insert_count != 3:
            print("FAILED: Expected 3 INSERT statements for 1200 rows (batches of 500).")
        else:
            print("PASSED: Batching logic seems correct.")

        # Check for ON CONFLICT count
        conflict_count = content.count("ON CONFLICT DO NOTHING;")
        print(f"Found {conflict_count} ON CONFLICT clauses.")
        
        if conflict_count != 3:
             print("FAILED: Expected 3 ON CONFLICT clauses.")
        else:
             print("PASSED: ON CONFLICT clause count matches.")

        # Check for syntax errors (e.g. ", ON CONFLICT")
        if ",\n ON CONFLICT" in content:
            print("FAILED: Found syntax error ', ON CONFLICT'")
        else:
            print("PASSED: No obvious syntax errors.")

if __name__ == "__main__":
    try:
        setup_db()
        run_export_test()
    except Exception as e:
        print(f"An error occurred: {e}")
