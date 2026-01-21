PrismDB Studio 🍃

PrismDB Studio is a comprehensive, lightweight, and user-friendly desktop GUI for MongoDB management, built with Python and PySide6. Designed to bridge the gap between SQL and NoSQL workflows, it provides advanced visualization tools, a relational-style data explorer, and real-time server monitoring—all without requiring complex command-line knowledge.

Whether you are a developer debugging queries, an administrator monitoring server health, or a data analyst exploring collections, PrismDB Studio offers a robust suite of tools to streamline your workflow.

🚀 Key Features

📊 Advanced Data Explorer
Relational View: View document data in a clean, table-like format.
CRUD Operations: Create, Read, Update, and Delete documents easily. Includes a built-in JSON editor for complex objects.
Smart Search: Simplified "Field : Value" search bar with auto-completion and type detection (automatically handles ObjectIds, Booleans, and Numbers).
Smart Pagination: Efficiently navigate through millions of documents.

🔗 Visual Tools

Relationship Visualizer: Automatically detects "Foreign Keys" (e.g., userId, order_id) and allows you to jump to the related document in another collection with a double-click.

ERD Visualizer: Scans your database schema to generate and export an Entity-Relationship Diagram (ERD) image.

Aggregation Builder: Build complex aggregation pipelines ($match, $group, $lookup, etc.) step-by-step visually and preview results instantly.

🛠️ Management & Optimization

Server Dashboard: Real-time health check showing active connections, memory usage, uptime, and operations per second.

Schema Manager: View and edit JSON Schema validation rules to enforce data integrity.

Index Manager: View, create, and drop indexes to optimize query performance.

Explain Plans: Analyze query performance visually to understand execution stats and identify bottlenecks.

⚡ Productivity

Multi-Tab Interface: Connect to multiple databases simultaneously in different tabs.

Query History & Bookmarks: Automatically saves your search history and allows you to "Star" complex queries for quick access.

Clipboard Import: "Paste as Docs" feature detects JSON or CSV data in your clipboard and imports it immediately.

Bulk Export/Import: Support for JSON, CSV, BSON, and SQL formats.

📦 Running the Pre-compiled Application

If you do not wish to install Python or dependencies, a standalone executable version is available.

Navigate to the exefile directory inside the project root.

You will see two essential folders:

dist: Contains the main executable application file.

build: Contains necessary system dependencies and build artifacts.

⚠️ CRITICAL: Both the dist and build folders must exist and be kept together for the software to function correctly. Do not separate them.

Open the dist folder.

Double-click main.exe (or PrismDBStudio.exe) to launch the application.

🛠️ Developer Setup (Run from Source)

To run the application from source code, ensure you have Python 3.10+ installed.

1. Clone the Repository

git clone [https://github.com/shivshankar263/PrismDB-Studio.git](https://github.com/shivshankar263/PrismDB-Studio.git)
cd prismdb-studio



2. Set up Virtual Environment

It is recommended to use a virtual environment to manage dependencies.

Windows:

python -m venv venv
.\venv\Scripts\activate



Mac/Linux:

python3 -m venv venv
source venv/bin/activate



3. Install Dependencies

pip install -r requirements.txt



4. Run the Application

python main.py



⌨️ Keyboard Shortcuts

Context

Shortcut

Action

Global

Ctrl + N

Open New Connection Tab



Ctrl + W

Close Current Tab



Ctrl + Tab

Switch to Next Tab



Ctrl + Q

Exit Application

Tab

F5 / Ctrl + Enter

Run Query / Refresh View



Ctrl + E

Export Data



Ctrl + O

Import Data



Ctrl + L

Focus Connection Bar

Pagination

Ctrl + Left

Previous Page



Ctrl + Right

Next Page

📂 Project Structure

prismdb_studio/
├── main.py                  # Application Entry Point
├── assets/                  # Icons and Stylesheets
├── config/                  # Global Settings
├── core/                    # Backend Logic (DB Manager, Workers)
├── gui/                     # Frontend UI
│   ├── dialogs/             # Popups (Export, Schema, Indexes)
│   ├── tabs/                # Main Tab Logic
│   ├── views/               # Specific Views (Data, Dashboard, Aggregation)
│   └── widgets/             # Reusable UI Components
└── utils/                   # Helpers (Query Manager, JSON tools)



📝 License

This project is open-source and available for educational and professional use.

Developed with ❤️ using Python & PySide6.