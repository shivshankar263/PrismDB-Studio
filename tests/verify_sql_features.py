
import os
import sys
import shutil
import time
import json
from pymongo import MongoClient
import threading
import queue

# Adjust path to import core.workers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.workers import worker_export_task

URI = "mongodb://localhost:27017"
DB_NAME = "test_export_features"
COLL_NAME = "feature_test"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output_feature_test")

def setup_db():
    client = MongoClient(URI)
    db = client[DB_NAME]
    db[COLL_NAME].drop()
    
    # Create data with nested objects
    data = [
        {
            "item": "Item A", 
            "details": {"color": "red", "size": 10}, 
            "tags": ["a", "b"]
        },
        {
            "item": "Item B", 
            "details": {"color": "blue", "size": 20}, 
            "tags": ["c"]
        }
    ]
    db[COLL_NAME].insert_many(data)
    client.close()

def run_export_test():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    q = queue.Queue()
    
    print("Testing SQL Export with Primary Key and JSON Storage...")
    try:
        # Enable add_pk=True, store_json=True
        worker_export_task(
            URI + "/" + DB_NAME, 
            OUTPUT_DIR, 
            "postgresql", 
            False, 
            False, 
            [COLL_NAME], 
            add_pk=True,
            store_json=True,
            queue=q
        )
    except Exception as e:
        print(f"Worker Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    pg_path = os.path.join(OUTPUT_DIR, f"{COLL_NAME}.sql")
    if not os.path.exists(pg_path):
        print("FAILED: Output file not found.")
        return

    with open(pg_path, "r", encoding="utf-8") as f:
        content = f.read()
        
        # 1. Verify Primary Key Column Definition
        if "id SERIAL PRIMARY KEY" in content:
            print("PASSED: Found 'id SERIAL PRIMARY KEY'")
        else:
            print("FAILED: Missing 'id SERIAL PRIMARY KEY'")

        # 2. Verify JSON Column Type (should be JSONB for postgresql)
        # We expect "details" JSONB and "tags" JSONB
        if '"details" JSONB' in content:
             print("PASSED: Found 'details' JSONB column")
        else:
             print("FAILED: Missing 'details' JSONB column")

        # 3. Verify INSERT VALUES have ID and JSON strings
        # Look for ID 1 and JSON string '{"color": "red", "size": 10}'
        if "'1'" in content or "(1," in content: 
             print("PASSED: Found ID value '1'")
        else:
             print("FAILED: Missing ID value '1'")

        # Check for serialized JSON
        if '{"color": "red", "size": 10}' in content:
             print("PASSED: Found serialized JSON string")
        else:
             print("FAILED: Missing serialized JSON string")

        # 4. Verify Encoding Header
        if "SET client_encoding = 'UTF8';" in content:
             print("PASSED: Found 'SET client_encoding = 'UTF8';'")
        else:
             print("FAILED: Missing encoding header")

if __name__ == "__main__":
    try:
        setup_db()
        run_export_test()
    except Exception as e:
        print(f"An error occurred: {e}")
