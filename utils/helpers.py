import json
from datetime import datetime
from bson import json_util, ObjectId
from dateutil.parser import parse as parse_date

def is_date_column(col_name):
    if not col_name: return False
    cl = col_name.lower()
    
    # User's specific mentions
    if cl in ["tsinmilliseconds", "tsinstr", "createdatms", "localizedtsinmilliseconds", "createdatstr"]:
        return True
        
    # General heuristics
    if "date" in cl or "time" in cl or "createdat" in cl or "updatedat" in cl or cl.startswith("ts"):
        return True
    return False

def parse_to_datetime(val):
    if isinstance(val, datetime): return val
    if isinstance(val, (int, float)):
        # Check if it's in milliseconds (usually > 10000000000 for dates past 1970)
        if val > 10000000000:
            return datetime.fromtimestamp(val / 1000.0)
        else:
            return datetime.fromtimestamp(val)
    if isinstance(val, str):
        try:
            return parse_date(val)
        except:
            pass
    return None

def map_mongo_type_to_pg(value):
    """Legacy helper for single value mapping (kept for compatibility)"""
    if value is None: return "TEXT"
    if isinstance(value, bool): return "BOOLEAN"
    if isinstance(value, int): return "BIGINT"
    if isinstance(value, float): return "NUMERIC"
    if isinstance(value, datetime): return "TIMESTAMP"
    if isinstance(val, ObjectId): return "TEXT"
    if isinstance(value, (dict, list)): return "JSONB"
    return "TEXT"

def resolve_sql_type(types_set, col_name=""):
    """
    Proper Fallback System:
    Analyzes a set of Python types found in a field and returns the safest SQL type.
    """
    if is_date_column(col_name):
        return "TIMESTAMP"
        
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
    
    # If we have dicts or lists mixed with other things, and JSON storage is intended,
    # we should prefer JSONB (or TEXT that contains JSON).
    # However, existing logic returns "TEXT" for mixed types which is also fine for JSON strings.
    # The key is that the caller needs to know to serialize it.
    
    # If mixed dicts and lists -> Use JSONB
    if all(t in (dict, list) for t in types_set):
        return "JSONB"

def sql_escape(val, col_name=""):
    if val is None: return "NULL"
    
    # Attempt to format identified date columns properly
    if is_date_column(col_name):
        dt = parse_to_datetime(val)
        if dt:
            return f"'{dt.strftime('%Y-%m-%d %H:%M:%S')}'"
            
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, datetime):
        # Format as YYYY-MM-DD HH:MM:SS for broad SQL compatibility
        return f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'"
    if isinstance(val, (dict, list)):
        return "'" + json.dumps(val, default=json_util.default).replace("'", "''") + "'"
    if isinstance(val, ObjectId):
        return f"'{str(val)}'"
    return "'" + str(val).replace("'", "''") + "'"

def filter_doc(doc, include_meta):
    if not include_meta:
        doc.pop('_id', None)
        doc.pop('__v', None)
    return doc