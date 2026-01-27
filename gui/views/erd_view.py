import math
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsItem,
    QGraphicsPathItem,
    QHBoxLayout,
    QPushButton,
    QGraphicsRectItem,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtGui import QPainter, QBrush, QColor, QPen, QFont, QPainterPath, QPolygonF
from PySide6.QtSvg import QSvgGenerator
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QSize

# --- CONSTANTS ---
NODE_WIDTH = 240
HEADER_HEIGHT = 35
ROW_HEIGHT = 25
PADDING = 10
GAP_X = 40
GAP_Y = 40

# Vivid Headers
HEADER_COLORS = [
    "#007bff",
    "#6610f2",
    "#6f42c1",
    "#e83e8c",
    "#dc3545",
    "#fd7e14",
    "#ffc107",
    "#28a745",
    "#20c997",
    "#17a2b8",
]


class RelationshipLine(QGraphicsPathItem):
    """Dynamic connection line (Curved Bezier)."""

    def __init__(self, start_item, end_item, parent=None):
        super().__init__(parent)
        self.start_item = start_item
        self.end_item = end_item

        # CRITICAL FIX: Z-Value -10 ensures lines are always BEHIND tables
        self.setZValue(-10)

        pen = QPen(QColor("#B0BEC5"), 2)
        pen.setStyle(Qt.SolidLine)
        self.setPen(pen)
        self.update_position()

    def update_position(self):
        if not self.start_item or not self.end_item:
            return

        # Map center points to scene coordinates
        p1 = self.start_item.sceneBoundingRect().center()
        p2 = self.end_item.sceneBoundingRect().center()

        path = QPainterPath()
        path.moveTo(p1)

        # Cubic Bezier for smooth curves
        ctrl1 = QPointF(p1.x() + 80, p1.y())
        ctrl2 = QPointF(p2.x() - 80, p2.y())
        path.cubicTo(ctrl1, ctrl2, p2)

        self.setPath(path)


class TableItem(QGraphicsRectItem):
    """
    Node representing a Collection.
    Inherits QGraphicsRectItem for robust bounding box handling.
    """

    def __init__(self, name, fields, x, y, color_index=0):
        field_count = len(fields) if fields else 1
        total_height = HEADER_HEIGHT + (field_count * ROW_HEIGHT) + PADDING

        super().__init__(0, 0, NODE_WIDTH, total_height)
        self.setPos(x, y)

        # CRITICAL FIX: Z-Value 10 ensures tables sit ON TOP of lines
        self.setZValue(10)

        self.name = name
        self.fields = fields if fields else {}
        self.lines = []

        self.header_color = QColor(HEADER_COLORS[color_index % len(HEADER_COLORS)])
        self.bg_color = QColor("white")
        self.border_color = QColor("#CFD8DC")

        self.font_header = QFont("Segoe UI", 11, QFont.Bold)
        self.font_field = QFont("Consolas", 10)
        self.font_small = QFont("Arial", 9)
        self.font_small.setItalic(True)

        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    def paint(self, painter, option, widget=None):
        r = self.rect()

        # 1. Background (Solid White to hide lines behind it)
        painter.setBrush(self.bg_color)
        painter.setPen(QPen(self.border_color, 1))
        painter.drawRoundedRect(r, 6, 6)

        # 2. Header Background
        header_rect = QRectF(r.x(), r.y(), r.width(), HEADER_HEIGHT)
        path = QPainterPath()
        path.addRoundedRect(header_rect, 6, 6)
        painter.save()
        painter.setClipRect(header_rect)
        painter.fillPath(path, self.header_color)
        painter.restore()

        # 3. Header Text
        painter.setPen(Qt.white)
        painter.setFont(self.font_header)
        text_rect = QRectF(
            r.x() + PADDING, r.y(), r.width() - 2 * PADDING, HEADER_HEIGHT
        )
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, self.name)

        # 4. Fields
        y = r.y() + HEADER_HEIGHT

        if not self.fields:
            painter.setPen(QColor("#999"))
            painter.setFont(self.font_small)
            painter.drawText(
                QRectF(r.x(), y, r.width(), ROW_HEIGHT),
                Qt.AlignCenter,
                "(No Fields Found)",
            )
        else:
            for field, f_type in self.fields.items():
                row_rect = QRectF(
                    r.x() + PADDING, y, r.width() - 2 * PADDING, ROW_HEIGHT
                )

                is_id = field == "_id" or field.endswith("_id") or field.endswith("Id")

                if is_id:
                    painter.setPen(self.header_color)
                    f = QFont(self.font_field)
                    f.setBold(True)
                    painter.setFont(f)
                else:
                    painter.setPen(Qt.black)
                    painter.setFont(self.font_field)

                painter.drawText(row_rect, Qt.AlignLeft | Qt.AlignVCenter, str(field))

                painter.setPen(QColor("#78909C"))
                painter.setFont(self.font_small)
                painter.drawText(row_rect, Qt.AlignRight | Qt.AlignVCenter, str(f_type))

                y += ROW_HEIGHT

    def add_connection(self, line):
        if line not in self.lines:
            self.lines.append(line)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            for line in self.lines:
                line.update_position()
        return super().itemChange(change, value)


class InteractiveGraphicsView(QGraphicsView):
    def __init__(self, scene, parent_erd):
        super().__init__(scene)
        self.parent_erd = parent_erd
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.viewport().setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        if self.parent_erd.is_linking_mode:
            item = self.itemAt(event.pos())
            while item and not isinstance(item, TableItem):
                item = item.parentItem()

            if isinstance(item, TableItem):
                self.parent_erd.start_linking(item, self.mapToScene(event.pos()))
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.parent_erd.is_linking_mode and self.parent_erd.temp_line:
            self.parent_erd.update_temp_line(self.mapToScene(event.pos()))
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.parent_erd.is_linking_mode and self.parent_erd.temp_line:
            item = self.itemAt(event.pos())
            while item and not isinstance(item, TableItem):
                item = item.parentItem()

            if isinstance(item, TableItem) and item != self.parent_erd.start_node:
                self.parent_erd.finish_linking(item)
            else:
                self.parent_erd.cancel_linking()
            return
        super().mouseReleaseEvent(event)


class ErdView(QWidget):
    request_schema_scan = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        # --- Toolbar ---
        toolbar = QHBoxLayout()

        self.btn_generate = QPushButton("🔄 Generate ERD")
        self.btn_generate.clicked.connect(self.emit_scan_request)

        self.btn_auto_link = QPushButton("🔗 Auto-Map (FK)")
        self.btn_auto_link.setToolTip("Auto-connect fields like 'user_id' to 'users'")
        self.btn_auto_link.clicked.connect(self.auto_connect_fk)

        self.btn_mode_link = QPushButton("✏️ Draw Connection")
        self.btn_mode_link.setCheckable(True)
        self.btn_mode_link.setToolTip("Manual Link: Click a table and drag to another")
        self.btn_mode_link.toggled.connect(self.toggle_link_mode)

        self.btn_export = QPushButton("📷 Export SVG")
        self.btn_export.clicked.connect(self.export_image_signal)

        toolbar.addWidget(self.btn_generate)
        toolbar.addWidget(self.btn_auto_link)
        toolbar.addWidget(self.btn_mode_link)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_export)
        self.layout.addLayout(toolbar)

        # --- Scene & View ---
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor("#F5F7FA")))
        self.view = InteractiveGraphicsView(self.scene, self)
        self.layout.addWidget(self.view)

        self.is_linking_mode = False
        self.temp_line = None
        self.start_node = None
        self.nodes_map = {}

    def emit_scan_request(self):
        self.request_schema_scan.emit()

    def export_image_signal(self):
        # NEW: SVG Export Logic
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Diagram", "erd_schema.svg", "SVG Files (*.svg)"
        )
        if path:
            generator = QSvgGenerator()
            generator.setFileName(path)
            generator.setSize(QSize(int(self.scene.width()), int(self.scene.height())))
            generator.setViewBox(self.scene.sceneRect())

            # Use a painter to render the scene into the SVG generator
            painter = QPainter()
            painter.begin(generator)
            self.scene.render(painter)
            painter.end()

            QMessageBox.information(self, "Export Successful", f"Saved to {path}")

    def render_schema(self, schema_data):
        self.scene.clear()
        self.nodes_map = {}

        # Masonry Layout
        COL_WIDTH = NODE_WIDTH + GAP_X
        num_cols = 4
        col_heights = [GAP_Y] * num_cols

        sorted_tables = sorted(schema_data.items(), key=lambda x: x[0])

        for i, (name, fields) in enumerate(sorted_tables):
            min_h = min(col_heights)
            col_idx = col_heights.index(min_h)

            x = GAP_X + (col_idx * COL_WIDTH)
            y = min_h

            item = TableItem(name, fields, x, y, color_index=i)
            self.scene.addItem(item)
            self.nodes_map[name] = item

            col_heights[col_idx] += item.rect().height() + GAP_Y

        max_h = max(col_heights)
        total_w = GAP_X + (num_cols * COL_WIDTH)
        self.scene.setSceneRect(0, 0, total_w, max_h + 100)

    def auto_connect_fk(self):
        if not self.nodes_map:
            return
        for source_name, source_item in self.nodes_map.items():
            for field in source_item.fields.keys():
                if field != "_id" and (field.endswith("_id") or field.endswith("Id")):
                    base = field.replace("_id", "").replace("Id", "").lower()
                    candidates = [base, base + "s", base + "es"]
                    if field in self.nodes_map:
                        candidates.append(field)

                    for t in candidates:
                        if t in self.nodes_map and t != source_name:
                            self.create_connection(source_item, self.nodes_map[t])
                            break

    def create_connection(self, start_item, end_item):
        line = RelationshipLine(start_item, end_item)
        self.scene.addItem(line)
        start_item.add_connection(line)
        end_item.add_connection(line)

    def toggle_link_mode(self, checked):
        self.is_linking_mode = checked
        if checked:
            self.view.setDragMode(QGraphicsView.NoDrag)
            self.view.viewport().setCursor(Qt.CrossCursor)
        else:
            self.view.setDragMode(QGraphicsView.ScrollHandDrag)
            self.view.viewport().setCursor(Qt.ArrowCursor)
            self.cancel_linking()

    def start_linking(self, item, pos):
        self.start_node = item
        self.temp_line = QGraphicsPathItem()
        pen = QPen(Qt.black, 2, Qt.DashLine)
        self.temp_line.setPen(pen)
        self.scene.addItem(self.temp_line)

    def update_temp_line(self, pos):
        if self.start_node and self.temp_line:
            start_pos = self.start_node.sceneBoundingRect().center()
            path = QPainterPath()
            path.moveTo(start_pos)
            path.lineTo(pos)
            self.temp_line.setPath(path)

    def finish_linking(self, end_item):
        if self.start_node and end_item:
            self.create_connection(self.start_node, end_item)
        self.cancel_linking()

    def cancel_linking(self):
        if self.temp_line:
            self.scene.removeItem(self.temp_line)
            self.temp_line = None
        self.start_node = None
