import sys
import os
import traceback
from unittest.mock import MagicMock, patch, mock_open

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from core.workers import worker_export_task

def debug_single_file_export():
    print("Starting debug...")
    try:
        with patch('core.workers.MongoClient') as mock_client, \
             patch('core.workers.open', new_callable=mock_open) as mock_file, \
             patch('core.workers.os.path.exists') as mock_exists, \
             patch('core.workers.time') as mock_time:
            
            # Setup
            mock_queue = MagicMock()
            mock_db = MagicMock()
            mock_client.return_value.get_default_database.return_value = mock_db
            mock_db.name = "testdb"
            mock_db.list_collection_names.return_value = ["coll1", "coll2"]
            
            # Mock Data - use real dicts
            mock_db["coll1"].find.return_value = [{"a": 1}, {"a": 2}]
            mock_db["coll2"].find.return_value = [{"b": "test"}]
            
            mock_time.time.return_value = 12345
            mock_exists.return_value = False 

            print("Calling worker_export_task...")
            worker_export_task("mongodb://localhost:27017/testdb", "C:/tmp", "sql", False, True, None, mock_queue)
            print("Finished worker_export_task")

            # Verify
            print(f"Open calls: {len(mock_file.mock_calls)}")
            for call in mock_file.mock_calls:
                print(call)

    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    debug_single_file_export()
