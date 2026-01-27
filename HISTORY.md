# History

All notable changes to the **PrismDB Studio** project will be documented in this file.

## [1.0.0] - 2026-01-27
### Added
- **Core GUI:** Complete multi-tabbed interface using PySide6 with a custom "Fusion" theme.
- **Data Explorer:**
  - Implemented tabular view for MongoDB documents.
  - Added "Smart Search" widget with auto-type detection for Int, Float, Boolean, and ObjectId.
  - Added "Foreign Key" detection to jump between related collections.
- **Aggregation Builder:** Visual tool to build pipelines stage-by-stage (`$match`, `$lookup`, `$group`).
- **Performance Tools:**
  - `ExplainDialog`: Visualizes `executionStats` and flags "Collection Scans" as critical warnings.
  - `DashboardView`: Real-time polling of connection pool, memory, and ops/sec.
- **Management:**
  - `IndexManager`: GUI for creating unique/compound indexes.
  - `SchemaDialog`: JSON editor for setting MongoDB validation rules.
  - `CreateCollectionDialog`: Support for Capped Collections and max documents.
- **Import/Export:**
  - Bulk Export worker supporting JSON, CSV, BSON, and **SQL** (auto-schema inference).
  - Clipboard Import: Auto-detects JSON or CSV from clipboard text.
- **Utilities:**
  - Query History and Bookmarking system (`query_manager.py`).
  - Dark/Light mode base styles defined in `styles.qss`.

### Fixed
- **Connection Bar:** Fixed layout stretching issues and added non-blocking "Connecting..." visual state.
- **Import Worker:** Handled `json_util` decoding errors for large files.
- **SQL Export:** Fixed type mapping for MongoDB `ObjectId` to PostgreSQL compatible text.

### Known Issues
- **GridFS:** `gridfs_view.py` is referenced but currently pending implementation.
- **Sorting:** Multi-column sorting is currently limited to single-field sort via table headers.