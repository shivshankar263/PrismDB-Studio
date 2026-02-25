<h1 align="center">
  <br>
  PrismDB Studio 🍃
  <br>
</h1>

<h4 align="center">A comprehensive, lightweight, and user-friendly desktop GUI for MongoDB management.</h4>

<p align="center">
  <a href="#key-features">Key Features</a> •
  <a href="#installation--setup">Installation</a> •
  <a href="#keyboard-shortcuts">Shortcuts</a> •
  <a href="#project-structure">Architecture</a> •
  <a href="#built-with">Built With</a>
</p>

---

**PrismDB Studio** bridges the gap between SQL and NoSQL workflows by offering a relational-style data explorer, advanced visualization tools, and real-time server monitoring—all without requiring complex command-line knowledge. Built with **Python** and **PySide6**.

## 🚀 Key Features

### 📊 Advanced Data Explorer
* **Relational View:** Table-based document viewer with structured columns instead of just nested JSON.
* **Smart Search:** Type-aware search bar that auto-detects ObjectIds, numbers, booleans, and strings.
* **Foreign Key Navigation:** Double-click `_id` fields to jump to related documents in other collections automatically.
* **Clipboard Import:** Paste JSON or CSV data directly from your clipboard into the collection.
* **Robust Data Import:**
  * **Memory-Safe Streaming:** Safely import large datasets (JSON Arrays up to 50MB+, JSONL, BSON) using streaming techniques instead of loading everything into memory.
  * **Graceful Fallbacks:** Handles bulk write errors by automatically skipping duplicate keys (`code 11000`) while preserving other valid documents during imports.
* **Advanced Export System:**
  * **Versatile Formats:** Export collections to standard formats including `.json`, `.csv`, `.bson`, and robust relational formats like plain `.sql` and `.postgresql`.
  * **Smart Schema Analysis:** Performs a full collection scan prior to CSV/SQL exports to dynamically map diverse NoSQL document structures to flat relational headers.
  * **Relational Conversion (SQL/PostgreSQL):** Convert MongoDB data to SQL inserts natively. Options include auto-generating Primary Keys (Auto-Increment / Serial), handling `_id` as either `TEXT` or `PRIMARY KEY`, and serializing nested JSON arrays/dicts gracefully.
  * **PostgreSQL Tweaks:** Generates valid PostgreSQL dumps complete with `SET client_encoding`, `standard_conforming_strings`, and `ON CONFLICT DO NOTHING` instructions for safe importing.

### 🛠 Visual Tools
* **Aggregation Builder:** Construct complex pipelines stage-by-stage (`$match`, `$group`, `$project`, etc.) without wrestling with nested JSON syntax.
* **ERD Visualizer:** Automatically scan your database schema and generate an Entity-Relationship Diagram (ERD) exportable to PNG.
* **GridFS Support:** View, upload, manage, and download large files stored in GridFS directly within the interface.
* **Schema Validation:** Edit and apply JSON Schema validation rules to collections easily.

### ⚡ Management & Performance
* **Real-time Dashboard:** Monitor active connections, memory usage, and operations per second.
* **Query Explain Plans:** Visual analysis of query performance with health checks (e.g., warnings for inefficient collection scans).
* **Index Manager:** Create, drop, and list indexes with a simple GUI.
* **Async Connection:** Non-blocking database connection handling keeps the GUI responsive.

---

## 📦 Installation & Setup

### Prerequisites
* Python 3.10+
* MongoDB Server (Local or Remote)

### Developer Setup (Running from Source)

1. **Clone the repository**
   ```bash
   git clone https://github.com/shivshankar263/prismdb-studio.git
   cd prismdb-studio
   ```

2. **Create a Virtual Environment**
   * **Windows:**
     ```bash
     python -m venv venv
     .\venv\Scripts\activate
     ```
   * **Mac/Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**
   ```bash
   python main.py
   ```

### Running the Standalone Executable
If you are using the pre-built version:
1. Navigate to the `exefile/dist` directory.
2. Ensure the `build` folder (dependencies) is present in the same directory.
3. Launch `main.exe` or `PrismDBStudio.exe`.

---

## ⌨️ Keyboard Shortcuts

| Context | Shortcut | Action |
| :--- | :--- | :--- |
| **Global** | `Ctrl + N` | Open New Connection Tab |
| | `Ctrl + W` | Close Current Tab |
| | `Ctrl + Tab` | Switch to Next Tab |
| | `Ctrl + Q` | Exit Application |
| **Tab / View** | `F5` / `Ctrl + Enter` | Run Query / Refresh View |
| | `Ctrl + E` | Export Data |
| | `Ctrl + O` | Import Data |
| | `Ctrl + L` | Focus Connection Bar |
| **Pagination** | `Ctrl + Left` | Previous Page |
| | `Ctrl + Right` | Next Page |

---

## 📂 Project Structure

```text
prismdb_studio/
├── main.py                  # Application Entry Point
├── settings.py              # Global Constants (Version, Defaults)
├── requirements.txt         # Project Dependencies
├── features.txt             # Feature List Reference
├── assets/                  # Icons and Stylesheets (styles.qss)
├── core/                    # Backend Logic
│   ├── db_manager.py        # Database Connection Handler
│   └── workers.py           # Background Tasks (Import/Export/Scan)
├── gui/                     # Frontend UI (PySide6)
│   ├── main_window.py       # Main Application Container
│   ├── dialogs/             # Popups (Create Collection, Explain, Index Manager)
│   ├── tabs/                # Tab Logic (db_tab.py)
│   ├── views/               # Feature Views (Data, Dashboard, Aggregation, ERD)
│   └── widgets/             # Reusable Components (ConnectionBar)
└── utils/                   # Helpers
    ├── helpers.py           # Type Mapping & SQL Escaping
    └── query_manager.py     # History & Bookmark Persistence