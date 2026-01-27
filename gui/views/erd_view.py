import math
import json
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
    QGraphicsDropShadowEffect,
)
from PySide6.QtGui import (
    QPainter,
    QBrush,
    QColor,
    QPen,
    QFont,
    QPainterPath,
    QPolygonF,
    QTransform,
    QWheelEvent,
)
from PySide6.QtSvg import QSvgGenerator
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QSize, QLineF

# --- CONSTANTS ---
NODE_WIDTH = 250
HEADER_HEIGHT = 40
ROW_HEIGHT = 28
PADDING = 10
GRID_SIZE = 40
GAP_X = 100
GAP_Y = 60

HEADER_COLORS = [
    "#2196F3",
    "#009688",
    "#FFC107",
    "#FF5722",
    "#9C27B0",
    "#3F51B5",
    "#4CAF50",
    "#795548",
    "#607D8B",
    "#E91E63",
]


class RelationshipLine(QGraphicsPathItem):
    """
    Orthogonal (Manhattan Style) connection line.
    Now stores the Foreign Key field name.
    """

    def __init__(self, start_item, end_item, fk_field=None, parent=None):
        super().__init__(parent)
        self.start_item = start_item
        self.end_item = end_item
        self.fk_field = fk_field  # Store the field name (e.g., 'user_id')
        self.setZValue(-1)

        # Style: Dark Gray, Sharp Corners
        pen = QPen(QColor("#546E7A"), 1.5)
        pen.setJoinStyle(Qt.RoundJoin)
        self.setPen(pen)

        self.arrow_head = QPolygonF()
        self.update_position()

    def update_position(self):
        if not self.start_item or not self.end_item:
            return

        # 1. Get Geometry (Right of Source -> Left of Target)
        rect1 = self.start_item.sceneBoundingRect()
        rect2 = self.end_item.sceneBoundingRect()

        p1 = QPointF(rect1.right(), rect1.center().y())
        p2 = QPointF(rect2.left(), rect2.center().y())

        path = QPainterPath()
        path.moveTo(p1)

        # 2. Orthogonal Routing Logic
        if p2.x() > p1.x():
            # Standard: Target is to the Right
            mid_x = p1.x() + (p2.x() - p1.x()) / 2
            path.lineTo(mid_x, p1.y())
            path.lineTo(mid_x, p2.y())
            path.lineTo(p2)
            angle = 0
        else:
            # Backward: Target is to the Left (Loop around)
            step_out = 20
            step_back = 20
            mid_y = (p1.y() + p2.y()) / 2

            path.lineTo(p1.x() + step_out, p1.y())
            path.lineTo(p1.x() + step_out, mid_y)
            path.lineTo(p2.x() - step_back, mid_y)
            path.lineTo(p2.x() - step_back, p2.y())
            path.lineTo(p2)
            angle = 0

        self.setPath(path)

        # 3. Draw Arrow Head
        arrow_size = 10
        p_tip = p2
        p_arrow_p1 = p_tip - QPointF(
            math.cos(angle + math.pi / 6) * arrow_size,
            math.sin(angle + math.pi / 6) * arrow_size,
        )
        p_arrow_p2 = p_tip - QPointF(
            math.cos(angle - math.pi / 6) * arrow_size,
            math.sin(angle - math.pi / 6) * arrow_size,
        )

        self.arrow_head = QPolygonF([p_tip, p_arrow_p1, p_arrow_p2])

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        painter.setBrush(QBrush(QColor("#546E7A")))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(self.arrow_head)


class TableItem(QGraphicsRectItem):
    """ERD Node"""

    def __init__(self, name, fields, x, y, color_index=0):
        field_count = len(fields) if fields else 1
        total_height = HEADER_HEIGHT + (field_count * ROW_HEIGHT) + PADDING

        super().__init__(0, 0, NODE_WIDTH, total_height)
        self.setPos(x, y)
        self.setZValue(10)

        self.name = name
        self.fields = fields if fields else {}
        self.lines = []

        self.header_color = QColor(HEADER_COLORS[color_index % len(HEADER_COLORS)])
        self.bg_color = QColor("#ffffff")
        self.border_color = QColor("#dce1e6")

        self.font_header = QFont("Segoe UI", 11, QFont.Bold)
        self.font_field = QFont("Consolas", 10)
        self.font_type = QFont("Consolas", 9)
        self.font_type.setItalic(True)

        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setGraphicsEffect(
            QGraphicsDropShadowEffect(
                blurRadius=15, xOffset=0, yOffset=4, color=QColor(0, 0, 0, 30)
            )
        )

    def paint(self, painter, option, widget=None):
        r = self.rect()

        # Box
        painter.setBrush(self.bg_color)
        painter.setPen(QPen(self.border_color, 1.5))
        painter.drawRoundedRect(r, 8, 8)

        # Header
        header_rect = QRectF(r.x(), r.y(), r.width(), HEADER_HEIGHT)
        path = QPainterPath()
        path.addRoundedRect(header_rect, 8, 8)
        painter.save()
        painter.setClipRect(header_rect)
        painter.fillPath(path, self.header_color)
        painter.restore()

        # Text
        painter.setPen(Qt.white)
        painter.setFont(self.font_header)
        painter.drawText(
            QRectF(r.x() + PADDING, r.y(), r.width() - 2 * PADDING, HEADER_HEIGHT),
            Qt.AlignLeft | Qt.AlignVCenter,
            self.name,
        )

        # Fields
        y = r.y() + HEADER_HEIGHT + 4
        if not self.fields:
            painter.setPen(QColor("#90A4AE"))
            painter.setFont(self.font_type)
            painter.drawText(
                QRectF(r.x(), y, r.width(), ROW_HEIGHT), Qt.AlignCenter, "(No Fields)"
            )
        else:
            for field, f_type in self.fields.items():
                row_rect = QRectF(
                    r.x() + PADDING, y, r.width() - 2 * PADDING, ROW_HEIGHT
                )

                is_id = field == "_id" or field.endswith("_id") or field.endswith("Id")
                if is_id:
                    painter.setPen(self.header_color.darker(110))
                    f = QFont(self.font_field)
                    f.setBold(True)
                    painter.setFont(f)
                else:
                    painter.setPen(QColor("#37474F"))
                    painter.setFont(self.font_field)

                painter.drawText(row_rect, Qt.AlignLeft | Qt.AlignVCenter, str(field))

                painter.setPen(QColor("#90A4AE"))
                painter.setFont(self.font_type)
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


class DiagramScene(QGraphicsScene):
    def drawBackground(self, painter, rect):
        painter.fillRect(rect, QColor("#F5F7FA"))

        left = int(rect.left()) - (int(rect.left()) % GRID_SIZE)
        top = int(rect.top()) - (int(rect.top()) % GRID_SIZE)

        points = []
        for x in range(left, int(rect.right()), GRID_SIZE):
            for y in range(top, int(rect.bottom()), GRID_SIZE):
                points.append(QPointF(x, y))

        painter.setPen(QPen(QColor("#CFD8DC"), 2))
        painter.drawPoints(points)


class InteractiveGraphicsView(QGraphicsView):
    def __init__(self, scene, parent_erd):
        super().__init__(scene)
        self.parent_erd = parent_erd
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.viewport().setCursor(Qt.ArrowCursor)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            zoom_in = event.angleDelta().y() > 0
            self.parent_erd.zoom(1.1 if zoom_in else 0.9)
            event.accept()
        else:
            super().wheelEvent(event)

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
        self.btn_auto_link.setToolTip(
            "Auto-connect fields and Separate Linked vs Isolated tables"
        )
        self.btn_auto_link.clicked.connect(self.auto_connect_fk)

        self.btn_mode_link = QPushButton("✏️ Draw Connection")
        self.btn_mode_link.setCheckable(True)
        self.btn_mode_link.clicked.connect(self.toggle_link_mode)

        self.btn_export = QPushButton("📷 Export SVG")
        self.btn_export.clicked.connect(self.export_image_signal)

        self.btn_export_json = QPushButton("📄 Export JSON")
        self.btn_export_json.clicked.connect(self.export_json_signal)

        self.btn_zoom_in = QPushButton("➕")
        self.btn_zoom_in.clicked.connect(lambda: self.zoom(1.2))
        self.btn_zoom_out = QPushButton("➖")
        self.btn_zoom_out.clicked.connect(lambda: self.zoom(0.8))

        toolbar.addWidget(self.btn_generate)
        toolbar.addWidget(self.btn_auto_link)
        toolbar.addWidget(self.btn_mode_link)
        toolbar.addWidget(self.btn_export)
        toolbar.addWidget(self.btn_export_json)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_zoom_out)
        toolbar.addWidget(self.btn_zoom_in)

        self.layout.addLayout(toolbar)

        self.scene = DiagramScene()
        self.view = InteractiveGraphicsView(self.scene, self)
        self.layout.addWidget(self.view)

        self.is_linking_mode = False
        self.temp_line = None
        self.start_node = None
        self.nodes_map = {}

    def emit_scan_request(self):
        self.request_schema_scan.emit()

    def zoom(self, factor):
        self.view.scale(factor, factor)

    def render_schema(self, schema_data):
        self.scene.clear()
        self.nodes_map = {}

        # Initial standard Grid Layout (mixed)
        COLUMNS = 4
        sorted_tables = sorted(schema_data.items(), key=lambda x: x[0])

        current_row_y = GAP_Y
        row_max_h = 0

        for i, (name, fields) in enumerate(sorted_tables):
            col = i % COLUMNS
            if col == 0 and i > 0:
                current_row_y += row_max_h + GAP_Y
                row_max_h = 0

            x = GAP_X + (col * (NODE_WIDTH + GAP_X))
            y = current_row_y

            item = TableItem(name, fields, x, y, color_index=i)
            self.scene.addItem(item)
            self.nodes_map[name] = item

            if item.rect().height() > row_max_h:
                row_max_h = item.rect().height()

        self.scene.setSceneRect(
            self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
        )

    def auto_connect_fk(self):
        """Creates connections AND separates Mapped vs Isolated tables."""
        if not self.nodes_map:
            return

        # 1. Create Connections
        for source_name, source_item in self.nodes_map.items():
            for field in source_item.fields.keys():
                if field != "_id" and (field.endswith("_id") or field.endswith("Id")):
                    base = field.replace("_id", "").replace("Id", "").lower()
                    candidates = [base, base + "s", base + "es"]
                    if field in self.nodes_map:
                        candidates.append(field)

                    for t in candidates:
                        if t in self.nodes_map and t != source_name:
                            # Pass the specific field that triggered the FK
                            self.create_connection(
                                source_item, self.nodes_map[t], fk_field=field
                            )
                            break

        # 2. Re-Layout: Separate Mapped vs Non-Mapped
        self.reorganize_layout()

    def reorganize_layout(self):
        """Moves mapped items to Left, isolated items to Right."""
        mapped_items = []
        isolated_items = []

        for name, item in self.nodes_map.items():
            if len(item.lines) > 0:
                mapped_items.append(item)
            else:
                isolated_items.append(item)

        def layout_group(items, start_x, start_y):
            cols = 3
            cur_y = start_y
            row_h = 0
            for i, item in enumerate(items):
                c = i % cols
                if c == 0 and i > 0:
                    cur_y += row_h + GAP_Y
                    row_h = 0

                x = start_x + (c * (NODE_WIDTH + GAP_X))
                y = cur_y

                item.setPos(x, y)
                if item.rect().height() > row_h:
                    row_h = item.rect().height()
            return start_x + (cols * (NODE_WIDTH + GAP_X))

        next_x = layout_group(mapped_items, GAP_X, GAP_Y)
        separator_x = next_x + 150
        layout_group(isolated_items, separator_x, GAP_Y)

        for item in self.nodes_map.values():
            for line in item.lines:
                line.update_position()

        self.scene.setSceneRect(
            self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
        )

    def create_connection(self, start_item, end_item, fk_field=None):
        # Prevent duplicate lines
        for line in start_item.lines:
            if line.end_item == end_item:
                return

        line = RelationshipLine(start_item, end_item, fk_field)
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

    def export_image_signal(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Diagram", "erd_schema.svg", "SVG Files (*.svg)"
        )
        if path:
            generator = QSvgGenerator()
            generator.setFileName(path)
            generator.setSize(QSize(int(self.scene.width()), int(self.scene.height())))
            generator.setViewBox(self.scene.sceneRect())

            painter = QPainter()
            painter.begin(generator)
            self.scene.render(painter)
            painter.end()
            QMessageBox.information(self, "Export Successful", f"Saved to {path}")

    def export_json_signal(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export JSON", "erd_schema.json", "JSON Files (*.json)"
        )
        if not path:
            return

        data = {"collections": {}, "relationships": []}

        # Export Nodes
        for name, item in self.nodes_map.items():
            data["collections"][name] = {
                "fields": item.fields,
                "x": item.x(),
                "y": item.y(),
            }

        # Export Relationships
        # Iterate over unique lines in the scene
        seen_lines = set()
        for item in self.nodes_map.values():
            for line in item.lines:
                if line in seen_lines:
                    continue
                seen_lines.add(line)

                rel = {
                    "source": line.start_item.name,
                    "target": line.end_item.name,
                    "fk_field": line.fk_field,
                }
                data["relationships"].append(rel)

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            QMessageBox.information(self, "Success", f"Exported to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save JSON: {e}")
