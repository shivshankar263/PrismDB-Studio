import os
import json
import csv
import time
import bson
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConfigurationError, BulkWriteError
from bson import json_util, ObjectId
from utils.helpers import map_mongo_type_to_pg, sql_escape, filter_doc, resolve_sql_type, to_snake_case, to_camel_case, flatten_dict


# --- IMPORT WORKER (Fixed: Streaming) ---
def worker_import_task(uri, files, queue):
    client = None
    try:
        client = MongoClient(uri)
        try:
            db = client.get_default_database()
        except ConfigurationError:
            db = client["test"]

        total_files = len(files)
        success_count = 0

        for idx, file_path in enumerate(files):
            filename = os.path.basename(file_path)
            coll_name = os.path.splitext(filename)[0]
            queue.put(
                ("progress", f"Importing {filename}...", int((idx / total_files) * 100))
            )

            try:
                coll = db[coll_name]
                ext = os.path.splitext(filename)[1].lower()

                def safe_insert_many(collection, docs):
                    try:
                        # ordered=False allows continuing even if some inserts fail (e.g. duplicates)
                        collection.insert_many(docs, ordered=False)
                    except BulkWriteError as bwe:
                        # Ignore duplicate key errors (code 11000), raise others
                        for err in bwe.details.get('writeErrors', []):
                            if err.get('code') != 11000:
                                raise bwe

                if ext == ".json":
                    # Improved JSON Import: Handle JSON Array stream or JSONL
                    with open(file_path, "r", encoding="utf-8") as f:
                        # Peek first char
                        first_char = f.read(1)
                        f.seek(0)
                        
                        if first_char == "[":
                            # Array Handling
                            file_size = os.path.getsize(file_path)
                            if file_size > 50 * 1024 * 1024: # 50MB
                                queue.put(("log", f"WARNING: Large JSON array '{filename}' ({file_size/1024/1024:.1f} MB). High Memory Usage!"))
                            
                            data = json.load(f, object_hook=json_util.object_hook)
                            if isinstance(data, list):
                                if data:
                                    batch_size = 1000
                                    for i in range(0, len(data), batch_size):
                                        safe_insert_many(coll, data[i:i+batch_size])
                            else:
                                try:
                                    coll.insert_one(data)
                                except Exception:
                                    pass # Skip duplicate for single insert too
                        
                        else:
                            # JSONL Handling
                            batch = []
                            for line in f:
                                line = line.strip()
                                if not line: continue
                                try:
                                    doc = json.loads(line, object_hook=json_util.object_hook)
                                    batch.append(doc)
                                    if len(batch) >= 1000:
                                        safe_insert_many(coll, batch)
                                        batch = []
                                except json.JSONDecodeError:
                                    continue 
                            if batch:
                                safe_insert_many(coll, batch)

                elif ext == ".bson":
                    # FIXED: Use decode_file_iter for true streaming
                    with open(file_path, "rb") as f:
                        batch = []
                        for doc in bson.decode_file_iter(f):
                            batch.append(doc)
                            if len(batch) >= 1000:
                                safe_insert_many(coll, batch)
                                batch = []
                        if batch:
                            safe_insert_many(coll, batch)

                success_count += 1
            except Exception as e:
                queue.put(("log", f"ERROR importing {filename}: {str(e)}"))
                continue

        queue.put(
            (
                "finished",
                f"Import job finished. Successfully imported {success_count}/{total_files} files.",
            )
        )
    except Exception as e:
        queue.put(("error", f"Critical Import Error: {str(e)}"))
    finally:
        if client:
            client.close()


# --- EXPORT WORKER (Fixed: Full Scan / Two-Pass) ---
def worker_export_task(uri, folder, fmt, include_meta, single_file, collections=None, add_pk=False, store_json=False, flatten_json=False, normalize=False, naming_conv="snake_case", pg_version=None, encoding="utf-8", limit=0, date_range=None, queue=None):
    """
    Export logic with Full Collection Scan for headers (CSV/SQL).
    """
    client = None
    try:
        client = MongoClient(uri)
        try:
            db = client.get_default_database()
        except ConfigurationError:
            queue.put(("error", "Database name missing in connection string."))
            return

        all_colls = db.list_collection_names()

        # Filter Logic
        filtered_colls = []
        filtered_colls = []
        if collections:
            filtered_colls = [c for c in all_colls if c in collections]
        else:
            filtered_colls = [
                c
                for c in all_colls
                if not c.startswith("system.")
                and not c.endswith(("metadata", "chunks", "files"))
            ]

        total = len(filtered_colls)
        if total == 0:
            queue.put(("finished", "No collections found to export."))
            return

        # Pre-calculate single file path if needed
        single_file_path = None
        single_file_path_norm = None
        
        format_func = to_snake_case if naming_conv == "snake_case" else to_camel_case
        
        if (fmt in ["sql", "postgresql"]) and single_file:
            single_file_path = os.path.join(folder, f"dump_{db.name}_{int(time.time())}.sql")
            with open(single_file_path, "w", encoding=encoding, errors="replace") as f:
                f.write(f"-- Export: {db.name} | {time.ctime()}\n")
                if fmt == "postgresql":
                    f.write(f"-- Target PostgreSQL Version: {pg_version}\n")
                    f.write(f"SET client_encoding = '{'UTF8' if encoding.lower() == 'utf-8' else 'ASCII'}';\n")
                    f.write("SET standard_conforming_strings = on;\n")
                    f.write("SET check_function_bodies = false;\n")
                    f.write("SET client_min_messages = warning;\n")
                f.write("BEGIN;\n\n")
            
            if normalize:
                single_file_path_norm = os.path.join(folder, f"dump_{format_func(db.name)}_{int(time.time())}_normalized.sql")
                with open(single_file_path_norm, "w", encoding=encoding, errors="replace") as f:
                    f.write(f"-- Export: {db.name} (Normalized, {naming_conv}) | {time.ctime()}\n")
                    if fmt == "postgresql":
                        f.write(f"-- Target PostgreSQL Version: {pg_version}\n")
                        f.write(f"SET client_encoding = '{'UTF8' if encoding.lower() == 'utf-8' else 'ASCII'}';\n")
                        f.write("SET standard_conforming_strings = on;\n")
                        f.write("SET check_function_bodies = false;\n")
                        f.write("SET client_min_messages = warning;\n")
                    f.write("BEGIN;\n\n")

        # Create Date Filter Query if provided
        date_query = {}
        if date_range:
            from_dt, to_dt = date_range
            
            from_dt = datetime.combine(from_dt, datetime.min.time())
            to_dt = datetime.combine(to_dt, datetime.max.time())
            
            # Generate fake ObjectIds for these dates to do a fast range check
            from_id = ObjectId.from_datetime(from_dt)
            to_id = ObjectId.from_datetime(to_dt)
            
            date_query = {"_id": {"$gte": from_id, "$lte": to_id}}

        for idx, name in enumerate(filtered_colls):
            queue.put(("progress", f"Exporting {name}...", int((idx / total) * 100)))

            try:
                if fmt in ["sql", "postgresql", "csv"]:
                    # --- PASS 1: Full Scan for Keys/Schema ---
                    queue.put(("log", f"Analyzing schema for {name} (Full Scan)..."))
                    
                    all_keys = set()
                    field_types = {} # For SQL
                    
                    # Optimized cursor for key scanning
                    projection = {} if fmt == "csv" else None # CSV only needs keys
                    cursor = db[name].find(date_query, projection=projection)
                    if limit > 0:
                        cursor = cursor.limit(limit)
                    
                    for doc in cursor:
                        doc = filter_doc(doc, include_meta)
                        if flatten_json:
                            # Strip _id temporarily to avoid flattening its nested parts if it's somehow an object, 
                            # though mostly it's to treat the rest of the doc as flat
                            doc_id = doc.pop('_id', None)
                            doc = flatten_dict(doc)
                            if doc_id is not None:
                                doc['_id'] = doc_id
                        
                        all_keys.update(doc.keys())
                        
                        if fmt != "csv": # Collect types for SQL
                            for key, val in doc.items():
                                if key == "_id": continue
                                if val is None: continue
                                t = type(val)
                                if isinstance(val, ObjectId): t = ObjectId
                                if isinstance(val, datetime): t = datetime
                                # If store_json is True, preserve dict/list types for resolution
                                if store_json and isinstance(val, (dict, list)):
                                    t = type(val) 
                                elif isinstance(val, (dict, list)):
                                     continue # Skip nested if not storing JSON (legacy behavior)
                                
                                if key not in field_types: field_types[key] = set()
                                field_types[key].add(t)

                    sorted_keys = sorted(list(all_keys))

                    # --- PASS 2: Write Data ---
                    
                    if fmt == "csv":
                        path = os.path.join(folder, f"{name}.{fmt}")
                        with open(path, "w", newline="", encoding=encoding, errors="replace") as f:
                            writer = csv.DictWriter(
                                f, fieldnames=sorted_keys, extrasaction="ignore"
                            )
                            writer.writeheader()
                            
                            cursor_write = db[name].find(date_query)
                            if limit > 0:
                                cursor_write = cursor_write.limit(limit)

                            for doc in cursor_write:
                                doc = filter_doc(doc, include_meta)
                                if flatten_json:
                                    doc_id = doc.pop('_id', None)
                                    doc = flatten_dict(doc)
                                    if doc_id is not None:
                                        doc['_id'] = doc_id
                                
                                # Flat conversion for nested objects
                                row = {}
                                for k in sorted_keys:
                                    v = doc.get(k, "")
                                    if isinstance(v, (dict, list, ObjectId)):
                                        row[k] = json_util.dumps(v)
                                    else:
                                        row[k] = v
                                writer.writerow(row)

                    elif fmt in ["sql", "postgresql"]:
                         runs = [False]
                         if normalize:
                             runs.append(True)
                         
                         for is_normalized in runs:
                             # Determine target file
                             if single_file:
                                 target_path = single_file_path_norm if is_normalized else single_file_path
                                 mode = "a"
                             else:
                                 suffix = "_normalized" if is_normalized else ""
                                 safe_name = format_func(name) if is_normalized else name
                                 target_path = os.path.join(folder, f"{safe_name}{suffix}.sql")
                                 mode = "w"
                             
                             with open(target_path, mode, encoding=encoding, errors="replace") as f:
                                if mode == "w":
                                    f.write(f"-- Export: {db.name} | Collection: {name} | {time.ctime()}\n")
                                    if fmt == "postgresql":
                                        f.write(f"-- Target PostgreSQL Version: {pg_version}\n")
                                        f.write(f"SET client_encoding = '{'UTF8' if encoding.lower() == 'utf-8' else 'ASCII'}';\n")
                                        f.write("SET standard_conforming_strings = on;\n")
                                        f.write("SET check_function_bodies = false;\n")
                                        f.write("SET client_min_messages = warning;\n")
                                    f.write("BEGIN;\n\n")

                                # Resolve SQL Types
                                columns = {}
                                col_mapping = {}
                                if add_pk:
                                    if fmt == "postgresql":
                                        columns["id"] = "SERIAL PRIMARY KEY"
                                    else:
                                        columns["id"] = "INTEGER PRIMARY KEY AUTOINCREMENT"
                                    col_mapping["id"] = "id"
                                
                                if include_meta:
                                    columns["_id"] = "TEXT" # Remove PK from _id if we have a real PK
                                    if not add_pk:
                                        columns["_id"] = "TEXT PRIMARY KEY"
                                    col_mapping["_id"] = "_id"

                                table_name = format_func(name) if is_normalized else name

                                for key, types_set in field_types.items():
                                    col_name = format_func(key) if is_normalized else key
                                    columns[col_name] = resolve_sql_type(types_set, key)
                                    col_mapping[col_name] = key

                                f.write(f"-- Table: {table_name}\n")
                                cols_def = ",\n    ".join([f'"{c}" {t}' for c, t in columns.items()])
                                f.write(f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n    {cols_def}\n);\n')

                                # Safer Insert Logic
                                start_stmt = f'INSERT INTO "{table_name}"'
                                end_stmt = ";"
                                
                                if fmt == "postgresql":
                                    end_stmt = " ON CONFLICT DO NOTHING;"
                                else: # sql
                                    start_stmt = f'INSERT OR IGNORE INTO "{table_name}"'

                                f.write(f'{start_stmt} ({", ".join([chr(34) + c + chr(34) for c in columns.keys()])}) VALUES\n')

                                batch = []
                                # Rewind cursor for data
                                cursor_write = db[name].find(date_query)
                                if limit > 0:
                                    cursor_write = cursor_write.limit(limit)

                                first_batch = True
                                pk_counter = 1
                                
                                for doc in cursor_write:
                                    doc = filter_doc(doc, include_meta)
                                    if flatten_json:
                                        doc_id = doc.pop('_id', None)
                                        doc = flatten_dict(doc)
                                        if doc_id is not None:
                                            doc['_id'] = doc_id
                                    
                                    vals = []
                                    for col in columns.keys():
                                        orig_key = col_mapping[col]
                                        if orig_key == "id" and add_pk:
                                            vals.append(str(pk_counter))
                                            continue
                                        
                                        val = doc.get(orig_key, None)
                                        if orig_key == "_id" and val is not None:
                                            val = str(val)
                                        
                                        # Handle JSON serialization if enabled and val is dict/list
                                        if store_json and isinstance(val, (dict, list)):
                                            val = json_util.dumps(val)

                                        vals.append(sql_escape(val, col))
                                    
                                    if add_pk: pk_counter += 1
                                    batch.append(f"({', '.join(vals)})")
                                    
                                    if len(batch) >= 500:
                                        # If not first batch, start a new INSERT statement
                                        if not first_batch:
                                            f.write(f'{start_stmt} ({", ".join([chr(34) + c + chr(34) for c in columns.keys()])}) VALUES\n')
                                        
                                        f.write(",\n".join(batch) + end_stmt + "\n\n")
                                        batch = []
                                        first_batch = False
                                
                                if batch:
                                    if not first_batch:
                                         f.write(f'{start_stmt} ({", ".join([chr(34) + c + chr(34) for c in columns.keys()])}) VALUES\n')
                                    f.write(",\n".join(batch) + end_stmt + "\n\n")

                                if mode == "w":
                                    f.write("COMMIT;\n")

                else:
                    # JSON/BSON (Already decent, but keeping consistency)
                    path = os.path.join(folder, f"{name}.{fmt}")
                    cursor = db[name].find(date_query)
                    if limit > 0:
                        cursor = cursor.limit(limit)
                    
                    if fmt == "json":
                        with open(path, "w", encoding=encoding, errors="replace") as f:
                            f.write("[\n")
                            first = True
                            for doc in cursor:
                                doc = filter_doc(doc, include_meta)
                                if not first: f.write(",\n")
                                f.write(json_util.dumps(doc))
                                first = False
                            f.write("\n]")
                    elif fmt == "bson":
                        with open(path, "wb") as f:
                            for doc in cursor:
                                doc = filter_doc(doc, include_meta)
                                f.write(bson.encode(doc))

            except Exception as e:
                queue.put(("log", f"Skipping {name} due to error: {e}"))
                continue

        if single_file_path:
             with open(single_file_path, "a", encoding=encoding, errors="replace") as f:
                 f.write("COMMIT;\n")
        if single_file_path_norm:
             with open(single_file_path_norm, "a", encoding=encoding, errors="replace") as f:
                 f.write("COMMIT;\n")

        queue.put(("finished", "Bulk Export Complete."))
    except Exception as e:
        queue.put(("error", str(e)))
    finally:
        if client:
            client.close()


# --- SCHEMA WORKER (Unchanged) ---
def worker_scan_schema(uri, queue):
    client = None
    try:
        client = MongoClient(uri)
        try:
            db = client.get_default_database()
        except ConfigurationError:
            queue.put(("error", "Database name missing."))
            return

        colls = db.list_collection_names()
        visible_colls = [c for c in colls if not c.startswith("system.")]

        schema_data = {}
        total = len(visible_colls)

        for idx, name in enumerate(visible_colls):
            queue.put(("progress", f"Analyzing {name}...", int((idx / total) * 100)))
            try:
                pipeline = [{"$sample": {"size": 20}}]
                samples = list(db[name].aggregate(pipeline))
                fields = {}
                for doc in samples:
                    for key, val in doc.items():
                        type_name = type(val).__name__
                        if isinstance(val, ObjectId):
                            type_name = "ObjectId"
                        fields[key] = type_name
                schema_data[name] = fields
            except Exception as e:
                queue.put(("log", f"Schema scan failed for {name}: {e}"))
                continue

        queue.put(("schema_result", json.dumps(schema_data)))
        queue.put(("finished", "Schema Analysis Complete."))
    except Exception as e:
        queue.put(("error", str(e)))
    finally:
        if client:
            client.close()
