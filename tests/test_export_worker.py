import unittest
from unittest.mock import MagicMock, patch, mock_open, call
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from core.workers import worker_export_task

class TestSQLExport(unittest.TestCase):
    @patch('core.workers.MongoClient')
    @patch('core.workers.open', new_callable=mock_open)
    @patch('core.workers.os.path.exists')
    @patch('core.workers.time')
    def test_single_file_export(self, mock_time, mock_exists, mock_file, mock_client):
        # Setup
        mock_queue = MagicMock()
        mock_db = MagicMock()
        mock_client.return_value.get_default_database.return_value = mock_db
        mock_db.name = "testdb"
        mock_db.list_collection_names.return_value = ["coll1", "coll2"]
        
        # Mock Data
        mock_db["coll1"].find.return_value = [{"a": 1}, {"a": 2}]
        mock_db["coll2"].find.return_value = [{"b": "test"}]
        
        mock_time.time.return_value = 12345
        mock_exists.return_value = False # New file

        # Execute
        # Execute
        worker_export_task("mongodb://localhost:27017/testdb", "C:/tmp", "sql", False, True, None, False, False, mock_queue)

        # Verify
        # Check if single file was opened
        mock_file.assert_called_with("C:/tmp\\dump_testdb_12345.sql", "a", encoding="utf-8")
        
        # Verify separate files were NOT created
        # The mock_file is called multiple times (for 'w' initially then 'a'), but always with the same path or read mode?
        # Wait, my implementation opens the single file with 'w' first, then 'a' inside the loop? 
        # Actually:
        # 1. Pre-calc path: open(single_file_path, "w") -> WRITE BEGIN
        # 2. Loop coll1: open(single_file_path, "a") -> WRITE TABLE
        # 3. Loop coll2: open(single_file_path, "a") -> WRITE TABLE
        # 4. Final: open(single_file_path, "a") -> WRITE COMMIT
        
        self.assertTrue(mock_file.call_count >= 4)
        handle = mock_file()
        
        # Check constraints
        # Should NOT see "coll1.sql" or "coll2.sql" in open calls
        for args, _ in mock_file.call_args_list:
            self.assertIn("dump_testdb_12345.sql", args[0])
            self.assertNotIn("coll1.sql", args[0])

    @patch('core.workers.MongoClient')
    @patch('core.workers.open', new_callable=mock_open)
    @patch('core.workers.time')
    def test_multi_file_export(self, mock_time, mock_file, mock_client):
        # Setup
        mock_queue = MagicMock()
        mock_db = MagicMock()
        mock_client.return_value.get_default_database.return_value = mock_db
        mock_db.name = "testdb"
        mock_db.list_collection_names.return_value = ["coll1", "coll2"]
        
        mock_db["coll1"].find.return_value = [{"a": 1}]
        mock_db["coll2"].find.return_value = [{"b": "test"}]
        mock_time.time.return_value = 12345

        # Execute
        # Execute
        worker_export_task("mongodb://localhost:27017/testdb", "C:/tmp", "sql", False, False, None, False, False, mock_queue)

        # Verify
        # Should open coll1.sql and coll2.sql
        opened_files = [args[0] for args, _ in mock_file.call_args_list]
        self.assertTrue(any("coll1.sql" in f for f in opened_files))
        self.assertTrue(any("coll2.sql" in f for f in opened_files))
        self.assertFalse(any("dump_testdb" in f for f in opened_files))

if __name__ == '__main__':
    unittest.main()
