import json
import os

HISTORY_FILE = "query_history.json"


class QueryManager:
    @staticmethod
    def load():
        if not os.path.exists(HISTORY_FILE):
            return {"history": [], "bookmarks": []}
        try:
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                # Ensure keys exist if file is old
                if "history" not in data:
                    data["history"] = []
                if "bookmarks" not in data:
                    data["bookmarks"] = []
                return data
        except:
            return {"history": [], "bookmarks": []}

    @staticmethod
    def save(data):
        with open(HISTORY_FILE, "w") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def add_to_history(query_str):
        data = QueryManager.load()
        if data["history"] and data["history"][0] == query_str:
            return
        if query_str in data["history"]:
            data["history"].remove(query_str)
        data["history"].insert(0, query_str)
        data["history"] = data["history"][:50]
        QueryManager.save(data)

    @staticmethod
    def add_bookmark(name, query_str):
        data = QueryManager.load()
        data["bookmarks"].append({"name": name, "query": query_str})
        QueryManager.save(data)

    # --- NEW: Clear History Only ---
    @staticmethod
    def clear_history():
        data = QueryManager.load()
        data["history"] = []  # Clear only history
        # Bookmarks are left untouched
        QueryManager.save(data)
