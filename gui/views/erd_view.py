from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem, QGraphicsItem
from PySide6.QtGui import QPainter, QBrush, QColor, QPen, QFont, QPixmap
from PySide6.QtCore import Qt, QRectF

class TableItem(QGraphicsRectItem):
    def __init__(self, name, fields, x, y):
        super().__init__(0, 0, 200, 35 + (len(fields) * 20))
        self.setPos(x, y)
        self.setBrush(QBrush(QColor("white")))
        self.setPen(QPen(QColor("#dee2e6"), 2))
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        
        self.name_text = QGraphicsTextItem(name, self)
        self.name_text.setFont(QFont("Arial", 10, QFont.Bold))
        self.name_text.setDefaultTextColor(QColor("white"))
        self.name_text.setPos(10, 5)
        
        self.header_bg = QGraphicsRectItem(0, 0, 200, 30, self)
        self.header_bg.setBrush(QBrush(QColor("#0d6efd")))
        self.header_bg.setPen(QPen(Qt.NoPen))
        self.header_bg.setZValue(-1)

        y_offset = 35
        for field, f_type in fields.items():
            f_text = QGraphicsTextItem(f"{field} : {f_type}", self)
            f_text.setFont(QFont("Consolas", 9))
            f_text.setPos(10, y_offset)
            y_offset += 20

class ErdView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        layout.addWidget(self.view)

    def render_schema(self, schema_data):
        self.scene.clear()
        x, y = 0, 0
        max_h = 0
        
        for name, fields in schema_data.items():
            item = TableItem(name, fields, x, y)
            self.scene.addItem(item)
            
            w = item.rect().width() + 50
            h = item.rect().height() + 50
            max_h = max(max_h, h)
            x += w
            
            if x > 1000:
                x = 0
                y += max_h
                max_h = 0

    def get_image(self):
        rect = self.scene.itemsBoundingRect()
        rect.adjust(-20, -20, 20, 20)
        img = QPixmap(rect.size().toSize())
        img.fill(Qt.white)
        ptr = QPainter(img)
        self.scene.render(ptr, target=QRectF(img.rect()), source=rect)
        ptr.end()
        return img