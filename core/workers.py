import os
import json
import csv
import time
import bson
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConfigurationError
from bson import json_util, ObjectId
from utils.helpers import map_mongo_type_to_pg, sql_escape, filter_doc, resolve_sql_type


# --- IMPORT WORKER (Unchanged) ---
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

                if ext == ".json":
                    with open(file_path, "r", encoding="utf-8") as f:
                        try:
                            data = json.load(f, object_hook=json_util.object_hook)
                            if isinstance(data, list):
                                if data:
                                    coll.insert_many(data)
                            else:
                                coll.insert_one(data)
                        except json.JSONDecodeError:
                            f.seek(0)
                            batch = []
                            for line in f:
                                if line.strip():
                                    batch.append(
                                        json.loads(
                                            line, object_hook=json_util.object_hook
                                        )
                                    )
                                    if len(batch) >= 1000:
                                        coll.insert_many(batch)
                                        batch = []
                            if batch:
                                coll.insert_many(batch)
                elif ext == ".bson":
                    with open(file_path, "rb") as f:
                        data = bson.decode_all(f.read())
                        if data:
                            for i in range(0, len(data), 5000):
                                coll.insert_many(data[i : i + 5000])
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


# --- EXPORT WORKER (Updated for PostgreSQL Fallback) ---
def worker_export_task(uri, folder, fmt, include_meta, target_colls, queue):
    """
    Export logic.
    Order of arguments MUST match start_process call:
    (uri, folder, fmt, meta, target_colls, queue)
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
        if target_colls:
            # Export only specific requested collections
            filtered_colls = [c for c in all_colls if c in target_colls]
        else:
            # Export ALL user collections
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

        # Handle both generic SQL and specific PostgreSQL requests
        if fmt in ["sql", "postgresql"]:
            file_name = f"dump_{db.name}_{int(time.time())}.sql"
            full_path = os.path.join(folder, file_name)

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(f"-- Export: {db.name} | {time.ctime()}\n")
                f.write(f"-- Format: {fmt.upper()}\nBEGIN;\n\n")

                for idx, name in enumerate(filtered_colls):
                    queue.put(
                        ("progress", f"SQL Export: {name}", int((idx / total) * 100))
                    )
                    try:
                        # 1. Analyze Schema with proper fallback logic
                        # Sample 100 docs to detect mixed types
                        sample_docs = list(db[name].find({}).limit(100))
                        if not sample_docs:
                            continue

                        # Track all unique types seen for each field
                        field_types = {} 

                        for doc in sample_docs:
                            doc = filter_doc(doc, include_meta)
                            for key, val in doc.items():
                                if key == "_id": continue
                                if val is None: continue
                                
                                # Identify Python Type
                                t = type(val)
                                if isinstance(val, ObjectId): t = ObjectId
                                if isinstance(val, datetime): t = datetime
                                
                                if key not in field_types:
                                    field_types[key] = set()
                                field_types[key].add(t)

                        # Resolve types using fallback logic
                        columns = {}
                        if include_meta:
                            columns["_id"] = "TEXT PRIMARY KEY"

                        for key, types_set in field_types.items():
                            columns[key] = resolve_sql_type(types_set)

                        if not columns:
                            continue

                        f.write(f"-- Table: {name}\n")
                        f.write(f'DROP TABLE IF EXISTS "{name}";\n')
                        cols_def = ",\n    ".join(
                            [f'"{c}" {t}' for c, t in columns.items()]
                        )
                        f.write(f'CREATE TABLE "{name}" (\n    {cols_def}\n);\n')

                        # 2. Write Data
                        f.write(
                            f'INSERT INTO "{name}" ({", ".join(['"' + c + '"' for c in columns.keys()])}) VALUES\n'
                        )

                        batch = []
                        cursor = db[name].find({})
                        for i, doc in enumerate(cursor):
                            doc = filter_doc(doc, include_meta)
                            vals = []
                            for col in columns.keys():
                                val = doc.get(col, None)
                                if col == "_id" and val is not None:
                                    val = str(val)
                                vals.append(sql_escape(val))
                            batch.append(f"({', '.join(vals)})")
                            if len(batch) >= 500:
                                f.write(",\n".join(batch) + ",\n")
                                batch = []

                        if batch:
                            f.write(",\n".join(batch) + ";\n\n")
                        else:
                            f.write(";\n\n")

                    except Exception as e:
                        queue.put(("log", f"Error exporting collection '{name}': {e}"))
                        continue

                f.write("COMMIT;\n")
        else:
            # JSON/CSV/BSON Logic (Unchanged)
            for idx, name in enumerate(filtered_colls):
                queue.put(
                    ("progress", f"Exporting {name}...", int((idx / total) * 100))
                )
                path = os.path.join(folder, f"{name}.{fmt}")
                try:
                    cursor = db[name].find({}).batch_size(2000)
                    if fmt == "json":
                        with open(path, "w", encoding="utf-8") as f:
                            f.write("[\n")
                            first = True
                            for doc in cursor:
                                doc = filter_doc(doc, include_meta)
                                if not first:
                                    f.write(",\n")
                                f.write(json_util.dumps(doc))
                                first = False
                            f.write("\n]")
                    elif fmt == "bson":
                        with open(path, "wb") as f:
                            for doc in cursor:
                                doc = filter_doc(doc, include_meta)
                                f.write(bson.encode(doc))
                    elif fmt == "csv":
                        sample = []
                        for doc in db[name].find({}).limit(100):
                            sample.append(filter_doc(doc, include_meta))
                        if not sample:
                            continue
                        headers = set()
                        for d in sample:
                            headers.update(d.keys())

                        cursor = db[name].find({})
                        with open(path, "w", newline="", encoding="utf-8") as f:
                            writer = csv.DictWriter(
                                f, fieldnames=list(headers), extrasaction="ignore"
                            )
                            writer.writeheader()
                            for doc in cursor:
                                doc = filter_doc(doc, include_meta)
                                row = {
                                    k: (
                                        json_util.dumps(v)
                                        if isinstance(v, (dict, list, ObjectId))
                                        else v
                                    )
                                    for k, v in doc.items()
                                }
                                writer.writerow(row)
                except Exception as e:
                    queue.put(("log", f"Skipping {name} due to error: {e}"))
                    continue

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
