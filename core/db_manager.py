from pymongo import MongoClient
from pymongo.errors import ConfigurationError, ConnectionFailure, OperationFailure


class DBManager:
    @staticmethod
    def connect(uri):
        """Attempts connection and returns (client, db, error_msg)"""
        try:
            # 1. Establish Connection (Time out faster: 3s)
            client = MongoClient(uri, serverSelectionTimeoutMS=3000)

            # 2. Verify Server Reachability
            client.server_info()

            # 3. Extract Database from URI
            try:
                db = client.get_default_database()
            except ConfigurationError:
                return (
                    None,
                    None,
                    "URI must include a database name.\nExample: mongodb://localhost:27017/mydb",
                )

            # 4. Verify Database-Specific Access (Auth Check)
            try:
                db.command("ping")
            except OperationFailure as e:
                return (
                    None,
                    None,
                    f"Authentication failed for database '{db.name}':\n{e}",
                )

            # 5. Strict Existence Check (Fix for 'Wrong DB Name')
            # Since MongoDB lazily creates DBs, we explicitly check if it exists
            # to prevent connecting to a typo (e.g., 'user' vs 'users').
            try:
                existing_dbs = client.list_database_names()
                if db.name not in existing_dbs:
                    # Sort suggestions to find close matches could be added here,
                    # but listing valid ones is a good start.
                    limit = 5
                    suggestion = ", ".join(existing_dbs[:limit])
                    if len(existing_dbs) > limit:
                        suggestion += ", ..."

                    return (
                        None,
                        None,
                        (
                            f"Database '{db.name}' does not exist on this server.\n"
                            f"Did you make a typo?\n\n"
                            # f"Available Databases:\n{suggestion}"
                        ),
                    )
            except OperationFailure:
                # If the user does not have permission to run 'listDatabases' (e.g. Atlas restricted user),
                # we skip this check and rely on the 'ping' above.
                pass

            return client, db, None

        except (ConnectionFailure, Exception) as e:
            return None, None, f"Connection Failed:\n{str(e)}"
