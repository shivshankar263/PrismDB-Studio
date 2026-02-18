import json
from datetime import datetime
from bson import json_util, ObjectId

def map_mongo_type_to_pg(value):
    """Legacy helper for single value mapping (kept for compatibility)"""
    if value is None: return "TEXT"
    if isinstance(value, bool): return "BOOLEAN"
    if isinstance(value, int): return "BIGINT"
    if isinstance(value, float): return "NUMERIC"
    if isinstance(value, datetime): return "TIMESTAMP"
    if isinstance(value, ObjectId): return "TEXT"
    if isinstance(value, (dict, list)): return "JSONB"
    return "TEXT"

def resolve_sql_type(types_set):
    """
    Proper Fallback System:
    Analyzes a set of Python types found in a field and returns the safest SQL type.
    """
    if not types_set:
        return "TEXT" # Default fallback for nulls
        
    # If only one type exists, map it directly
    if len(types_set) == 1:
        t = list(types_set)[0]
        if t == bool: return "BOOLEAN"
        if t == int: return "BIGINT"
        if t == float: return "NUMERIC"
        if t == datetime: return "TIMESTAMP"
        if t == dict or t == list: return "JSONB"
        return "TEXT"

    # --- FALLBACK LOGIC ---
    # If mixed integers and floats -> Use NUMERIC to be safe
    if all(t in (int, float) for t in types_set):
        return "NUMERIC"
    
    # If mixed dicts and lists -> Use JSONB
    if all(t in (dict, list) for t in types_set):
        return "JSONB"

    # If any other mix (e.g., String + Int), fallback to TEXT to prevent data loss
    return "TEXT"

def sql_escape(val):
    if val is None: return "NULL"
    if isinstance(val, (dict, list)):
        return "'" + json.dumps(val, default=json_util.default).replace("'", "''") + "'"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, datetime):
        return f"'{val.isoformat()}'"
    if isinstance(val, ObjectId):
        return f"'{str(val)}'"
    return "'" + str(val).replace("'", "''") + "'"

def filter_doc(doc, include_meta):
    if not include_meta:
        doc.pop('_id', None)
        doc.pop('__v', None)
    return doc