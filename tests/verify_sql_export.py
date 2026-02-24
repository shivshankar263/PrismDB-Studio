
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
COLL_NAME = "dummy"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output_safety_test")

def setup_db():
    client = MongoClient(URI)
    db = client[DB_NAME]
    db[COLL_NAME].drop()
    db[COLL_NAME].insert_many([
        {"item": "A", "price": 10},
        {"item": "B", "price": 20},
        {"item": "C", "price": 30}
    ])
    client.close()

def run_export_test():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    q = queue.Queue()
    
    # 1. Test Generic SQL (sql)
    print("Testing Generic SQL...")
    worker_export_task(URI + "/" + DB_NAME, OUTPUT_DIR, "sql", False, False, [COLL_NAME], q)
    
    sql_path = os.path.join(OUTPUT_DIR, f"{COLL_NAME}.sql")
    with open(sql_path, "r", encoding="utf-8") as f:
        content = f.read()
        if "CREATE TABLE IF NOT EXISTS" not in content:
            print("FAILED: Generic SQL missing CREATE TABLE IF NOT EXISTS")
        else:
            print("PASSED: Generic SQL has CREATE TABLE IF NOT EXISTS")
            
        if "INSERT OR IGNORE INTO" not in content:
            print("FAILED: Generic SQL missing INSERT OR IGNORE")
        else:
            print("PASSED: Generic SQL has INSERT OR IGNORE")

    # 2. Test PostgreSQL (postgresql)
    print("\nTesting PostgreSQL...")
    # Clean up for next run (file name clash handling effectively overwrites in w mode, but let's be clean)
    os.rename(sql_path, sql_path + ".bak") 
    
    worker_export_task(URI + "/" + DB_NAME, OUTPUT_DIR, "postgresql", False, False, [COLL_NAME], q)
    
    pg_path = os.path.join(OUTPUT_DIR, f"{COLL_NAME}.sql")
    with open(pg_path, "r", encoding="utf-8") as f:
        content = f.read()
        if "CREATE TABLE IF NOT EXISTS" not in content:
            print("FAILED: PostgreSQL missing CREATE TABLE IF NOT EXISTS")
        else:
            print("PASSED: PostgreSQL has CREATE TABLE IF NOT EXISTS")

        if "ON CONFLICT DO NOTHING;" not in content:
            print(f"FAILED: PostgreSQL missing ON CONFLICT DO NOTHING. Content snippet:\n{content[-100:]}")
        else:
            print("PASSED: PostgreSQL has ON CONFLICT DO NOTHING")

if __name__ == "__main__":
    try:
        setup_db()
        run_export_test()
    except Exception as e:
        print(f"An error occurred: {e}")
