# PrismDB Studio 🍃

**PrismDB Studio** is a comprehensive, lightweight, and user-friendly desktop GUI for MongoDB management. Built with **Python** and **PySide6**, it bridges the gap between SQL and NoSQL workflows by offering a relational-style data explorer, advanced visualization tools, and real-time server monitoring—all without requiring complex command-line knowledge.

---

## 🚀 Key Features

### 📊 Advanced Data Explorer
* **Relational View:** View MongoDB collections as tables with structured columns.
* **Smart Search:** Simple search bar with type inference (auto-detects numbers, booleans, and ObjectIds).
* **Foreign Key Navigation:** Double-click `_id` fields to jump to related documents in other collections automatically.
* **Productivity:** Import JSON/CSV directly from your clipboard.

### 🛠 Visual Tools
* **Aggregation Builder:** Construct complex pipelines stage-by-stage (`$match`, `$group`, etc.) without wrestling with nested JSON syntax.
* **ERD Visualizer:** Automatically scan your database schema and generate an Entity-Relationship Diagram (ERD) exportable to PNG.
* **GridFS Support:** Manage large files directly within the interface.

### ⚡ Management & Performance
* **Real-time Dashboard:** Monitor active connections, memory usage, and operations per second.
* **Query Explain Plans:** Visual analysis of query performance with health checks (warnings for inefficient collection scans).
* **Index Manager:** Create, drop, and list indexes with a simple GUI.
* **Schema Validation:** Edit and apply JSON Schema validation rules to collections.

---

## 📦 Installation & Setup

### Prerequisites
* Python 3.10+
* MongoDB Server (Local or Remote)

### Developer Setup (Running from Source)

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/your-username/prismdb-studio.git](https://github.com/your-username/prismdb-studio.git)
    cd prismdb-studio
    ```

2.  **Create a Virtual Environment**
    * *Windows:*
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```
    * *Mac/Linux:*
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Application**
    ```bash
    python main.py
    ```

### Running the Standalone Executable
If using the pre-built version:
1.  Navigate to the `exefile/dist` directory.
2.  Ensure the `build` folder (dependencies) is present in the same directory.
3.  Launch `main.exe` or `PrismDBStudio.exe`.

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