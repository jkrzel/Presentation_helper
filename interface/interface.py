import sys, math
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPainter, QPainterPath, QBrush, QLinearGradient, QColor, QPixmap, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QLabel, QPushButton, QTabBar
)

def rounded_cog_path(center: QPointF, radius: float, teeth: int = 8, inner_ratio: float = 0.7, corner_round: float = 0.2) -> QPainterPath:
    """Tworzy kształt przypominający koło z zębatkami (cog)."""
    path = QPainterPath()
    angle_step = 2 * math.pi / (teeth * 2)
    pts = []
    for i in range(teeth * 2):
        r = radius if i % 2 == 0 else radius * inner_ratio
        angle = i * angle_step
        pts.append(QPointF(center.x() + r * math.cos(angle), center.y() + r * math.sin(angle)))
    for i, p in enumerate(pts):
        prev = pts[i - 1]
        nxt = pts[(i + 1) % len(pts)]
        v1 = prev + (p - prev) * corner_round
        v2 = nxt + (p - nxt) * corner_round
        if i == 0:
            path.moveTo(v1)
        else:
            path.lineTo(v1)
        path.quadTo(p, v2)
    path.closeSubpath()
    return path

class CogBackgroundWidget(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0, QColor("#2e2e5c"))
        grad.setColorAt(1, QColor("#5c7bd1"))
        painter.fillRect(self.rect(), QBrush(grad))
        painter.setRenderHint(QPainter.Antialiasing)
        brush = QBrush(QColor(255, 255, 255, 7))
        for fx, fy, szf in [(0.3,0.4,0.25),(0.7,0.6,0.35),(0.5,0.2,0.2),(-0.1,0.3,0.25),(-1,-0.5,-0.1),(0.6,0.5,0.4),(-0.6,0.9,0.4)]:
            outer = min(self.width(), self.height()) * szf
            center = QPointF(self.width()*fx, self.height()*fy)
            path = rounded_cog_path(center, outer)
            painter.fillPath(path, brush)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Ustawienia ikony i stylu okna
        self.setWindowIcon(QIcon("logo.jpg"))  # ścieżka do logo
        self.setStyleSheet("QMainWindow { background-color: #1e1e3f; }")
        self.setWindowTitle("Presentation Helper")
        self.setMinimumSize(800, 600)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0,0,0,0)

        sidebar = QListWidget()
        sidebar.addItems(["left mouse","right mouse","resize","scroll","action circle"])
        # Wyśrodkowanie tekstu w każdej pozycji na liście
        for i in range(sidebar.count()):
            item = sidebar.item(i)
            item.setTextAlignment(Qt.AlignCenter)

        sidebar.setFixedWidth(150)
        #sidebar.setStyleSheet("background: rgba(99, 99, 171,0.1); color:#b3b3e3; border: none;")
        sidebar.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                color: #b3b3e3;
            }
            QListWidget::item {
                padding: 10px 16px;
                margin: 4px;
                background: rgba(40, 40, 69, 0.2);
                border-radius: 6px;
            }
            QListWidget::item:hover {
                background: rgba(90, 90, 150, 0.4);
                color: white;
            }
            QListWidget::item:selected {
                background: rgba(120, 120, 200, 0.5);
                color: white;
            }
        """)

        main_layout.addWidget(sidebar)

        content = CogBackgroundWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16,16,16,16)
        main_layout.addWidget(content)

        top_bar = QWidget(content)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0,0,0,0)
        logo_lbl = QLabel()
        top_bar = QWidget(content)
        top_bar.setStyleSheet("background: rgba(30,30,63,0.8);")
        top_layout = QHBoxLayout(top_bar)
        top_layout.addWidget(logo_lbl)
        tabs = QTabBar()
        tabs.addTab("set1")
        tabs.addTab("set2")
        tabs.addTab("set3")
        tabs.addTab("set4")
        tabs.addTab("set5")
        tabs.setStyleSheet(
            "QTabBar::tab { padding:8px 16px; background: rgba(255,255,255,0.1); color:white; margin-left:4px;}"
            "QTabBar::tab:selected { background: rgba(255,255,255,0.2); }"
        )
        top_layout.addWidget(tabs)
        top_layout.addStretch()
        content_layout.addWidget(top_bar)

        filler = QWidget(content)
        filler.setSizePolicy(filler.sizePolicy().Expanding, filler.sizePolicy().Expanding)
        content_layout.addWidget(filler)

        new_btn = QPushButton("New session", filler)
        new_btn.setIcon(QIcon.fromTheme("document-new"))
        new_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.8); padding:8px 12px; border-radius:6px;}"
            "QPushButton:hover { background: rgba(255,255,255,1.0); }"
        )
        new_btn.adjustSize()
        new_btn.move(filler.width()-new_btn.width()-20, filler.height()-new_btn.height()-20)
        new_btn.show()

        def on_resize(e):
            fw, fh = filler.width(), filler.height()
            #info_tile.move(fw-info_tile.width()-20, 20)
            new_btn.move(fw-new_btn.width()-20, fh-new_btn.height()-20)
        filler.resizeEvent = on_resize

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
