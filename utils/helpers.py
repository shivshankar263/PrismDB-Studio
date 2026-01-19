import json
from datetime import datetime
from bson import json_util, ObjectId

def map_mongo_type_to_pg(value):
    if value is None: return "TEXT"
    if isinstance(value, bool): return "BOOLEAN"
    if isinstance(value, int): return "BIGINT"
    if isinstance(value, float): return "NUMERIC"
    if isinstance(value, datetime): return "TIMESTAMP"
    if isinstance(value, ObjectId): return "TEXT"
    if isinstance(value, (dict, list)): return "JSONB"
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