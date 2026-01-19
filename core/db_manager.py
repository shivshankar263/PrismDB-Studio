from pymongo import MongoClient
from pymongo.errors import ConfigurationError, ConnectionFailure

class DBManager:
    @staticmethod
    def connect(uri):
        """Attempts connection and returns (client, db, error_msg)"""
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            client.server_info()  # Trigger connection check
            
            try: 
                db = client.get_default_database()
            except ConfigurationError:
                return None, None, "URI must include a database name.\nExample: mongodb://localhost:27017/mydb"
            
            return client, db, None
        except (ConnectionFailure, Exception) as e:
            return None, None, str(e)