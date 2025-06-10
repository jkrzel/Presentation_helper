import sys
import math
import subprocess
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QListWidget, QComboBox, QMainWindow
)
from PyQt5.QtGui import (
    QFontDatabase, QFont, QPixmap, QIcon,
    QPainter, QPainterPath, QBrush, QLinearGradient, QColor
)
from PyQt5.QtCore import Qt, QPointF, QTimer

# Paths for engine script and session config
ENGINE_SCRIPT = "tydz_VII_inżynieria.py"
CONFIG_FILE   = "session_config.json"

# Helper to create gear shapes
def gear_with_hole_path(center: QPointF,
                        radius: float,
                        teeth: int = 8,
                        tooth_depth: float = 0.2,
                        tooth_width: float = 0.6,
                        hole_ratio: float = 0.4,
                        corner_radius: float = None) -> QPainterPath:
    if corner_radius is None:
        corner_radius = radius * 0.05
    path = QPainterPath()
    outer_r = radius
    inner_r = radius * (1 - tooth_depth)
    ang_step = 2 * math.pi / teeth
    half_tooth = ang_step * tooth_width / 2
    def pp(r, a): return QPointF(center.x() + r * math.cos(a), center.y() + r * math.sin(a))
    for i in range(teeth):
        base = i * ang_step
        a0, a1 = base - half_tooth, base + half_tooth
        p0, p1 = pp(inner_r, a0), pp(outer_r, a0)
        p2, p3 = pp(outer_r, a1), pp(inner_r, a1)
        if i == 0:
            path.moveTo(p0)
        else:
            path.lineTo(p0)
        if corner_radius > 0:
            path.lineTo(p1)
            path.quadTo(pp(outer_r + corner_radius, base), p2)
        else:
            path.lineTo(p1)
            path.lineTo(p2)
        path.lineTo(p3)
    path.closeSubpath()
    hole_r = radius * hole_ratio
    path.addEllipse(center, hole_r, hole_r)
    path.setFillRule(Qt.OddEvenFill)
    return path

class CogBackgroundWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rot = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)
    def animate(self):
        self.rot = (self.rot + 1) % 360
        self.update()
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0, QColor("#2e2e5c")); grad.setColorAt(1, QColor("#5c7bd1"))
        p.fillRect(self.rect(), QBrush(grad))
        brush = QBrush(QColor(255,255,255,7))
        gears = [(0.2,0.3,0.15),(0.5,0.5,0.35),(0.8,0.2,0.2),(0.8,0.7,0.25),
                 (0.3,0.75,0.18),(0.6,0.35,0.12),(0.4,0.2,0.1)]
        for i,(fx,fy,sz) in enumerate(gears):
            R = min(self.width(), self.height()) * sz
            cen = QPointF(self.width()*fx, self.height()*fy)
            p.save()
            ang = self.rot * (1 + 0.3 * i)
            p.translate(cen); p.rotate(ang); p.translate(-cen)
            gp = gear_with_hole_path(cen, R/2, teeth=8, tooth_depth=0.25, corner_radius=(R/2)*0.1)
            p.setBrush(brush); p.setPen(Qt.NoPen); p.drawPath(gp)
            p.restore()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("logo.jpg"))
        self.setStyleSheet("QMainWindow { background-color: #1e1e3f; }")
        self.setWindowTitle("Presentation Helper")
        self.setMinimumSize(1300, 900)
        self.sidebar_idx = -1
        self.session_proc = None

        central = QWidget(); self.setCentralWidget(central)
        ml = QHBoxLayout(central); ml.setContentsMargins(0,0,0,0)

        # Sidebar
        self.sidebar = QListWidget(); self.sidebar.setFocusPolicy(Qt.NoFocus)
        self.sidebar.addItems(["left mouse","right mouse","resize","scroll","action circle"])
        self.sidebar.setFixedWidth(150)
        self.sidebar.setStyleSheet(
            "QListWidget{background:transparent;border:none;color:white;}"
            "QListWidget::item{padding:8px;margin:4px;background:rgba(40,40,69,0.2);border-radius:6px;}"
            "QListWidget::item:hover{background:rgba(90,90,150,0.4);}"
            "QListWidget::item:selected{background:rgba(120,120,200,0.5);}"
        )
        self.sidebar.itemClicked.connect(self.on_sidebar_item_clicked)
        ml.addWidget(self.sidebar)

        # Sidebar description
        self.sidebar_desc = QWidget(); sd = QVBoxLayout(self.sidebar_desc); sd.setContentsMargins(8,8,8,8)
        self.desc_label = QLabel(); self.desc_label.setStyleSheet("color:white;"); self.desc_label.setWordWrap(True)
        self.img_label = QLabel(); self.img_label.setAlignment(Qt.AlignCenter)
        sd.addWidget(self.desc_label); sd.addWidget(self.img_label)
        self.sidebar_desc.setFixedWidth(200); self.sidebar_desc.setVisible(False)
        ml.addWidget(self.sidebar_desc)

        self.descriptions = {
            "left mouse":("select and drag.","images/1.png"),
            "right mouse":("context menu.","images/2.png"),
            "resize":("change window size.","images/3.png"),
            "scroll":("wheel moves content.","images/4.png"),
            "action circle":("special gesture.","images/5.png"),
        }

        # Content + topbar + settings panel
        content = CogBackgroundWidget(); cl = QVBoxLayout(content); cl.setContentsMargins(16,16,16,16)
        ml.addWidget(content)

        # Topbar
        topbar = QWidget(content); topbar.setStyleSheet("background:rgba(30,30,63,0.8);")
        tl = QHBoxLayout(topbar); tl.setContentsMargins(10,4,10,4); tl.setSpacing(20)
        self.buttons = []
        for name in ("Camera Resolution","Mirror Transparency","Gesture Recognition","Cursor Motion Smoothing"):
            b = QPushButton(name); b.setCheckable(True)
            b.setStyleSheet(
                "QPushButton{background:rgba(40,40,69,0.2);color:white;border-radius:6px;padding:4px 8px;}"
                "QPushButton:hover{background:rgba(90,90,150,0.4);}"
                "QPushButton:checked{background:rgba(120,120,200,0.5);}"
            )
            tl.addWidget(b); self.buttons.append(b)
        tl.addStretch(); cl.addWidget(topbar)

        # Settings panel
        self.panel = QWidget(content); self.panel.setStyleSheet("background:rgba(50,50,90,0.9);border-radius:10px;")
        pl = QVBoxLayout(self.panel); pl.setContentsMargins(12,12,12,12); self.panel.setVisible(False)

        # Widgets: cam_combo, mirror slider, gesture combo, cursor sliders
        self.cam_combo = QComboBox(); self.cam_combo.addItems(["Low","Medium","High"])
        self.mirror_slider = QSlider(Qt.Horizontal); self.mirror_slider.setRange(0,100)
        self.mirror_val = QLabel("0"); self.mirror_slider.valueChanged.connect(lambda v:self.mirror_val.setText(str(v)))
        mw = QWidget(); mlm = QHBoxLayout(mw); mlm.setContentsMargins(0,0,0,0)
        mlm.addWidget(self.mirror_slider); mlm.addWidget(self.mirror_val)

        self.gesture_combo = QComboBox(); self.gesture_combo.addItems(["Low","Medium","High"])

        self.epsilon_slider = QSlider(Qt.Horizontal); self.epsilon_slider.setRange(0,100)
        self.epsilon_val    = QLabel("0"); self.epsilon_slider.valueChanged.connect(lambda v:self.epsilon_val.setText(str(v)))
        eps_w = QWidget(); eps_l = QVBoxLayout(eps_w); eps_l.setContentsMargins(0,0,0,0)
        eps_l.addWidget(QLabel("epsilon", alignment=Qt.AlignCenter))
        row1 = QWidget(); r1 = QHBoxLayout(row1); r1.setContentsMargins(0,0,0,0)
        r1.addWidget(self.epsilon_slider); r1.addWidget(self.epsilon_val); eps_l.addWidget(row1)

        self.interp_slider = QSlider(Qt.Horizontal); self.interp_slider.setRange(0,100)
        self.interp_val    = QLabel("0"); self.interp_slider.valueChanged.connect(lambda v:self.interp_val.setText(str(v)))
        int_w = QWidget(); int_l = QVBoxLayout(int_w); int_l.setContentsMargins(0,0,0,0)
        int_l.addWidget(QLabel("interpolation", alignment=Qt.AlignCenter))
        row2 = QWidget(); r2 = QHBoxLayout(row2); r2.setContentsMargins(0,0,0,0)
        r2.addWidget(self.interp_slider); r2.addWidget(self.interp_val); int_l.addWidget(row2)

        self.cursor_widget = QWidget(); cwl = QVBoxLayout(self.cursor_widget); cwl.setContentsMargins(0,0,0,0)
        cwl.addWidget(eps_w); cwl.addWidget(int_w)

        for w in (self.cam_combo, mw, self.gesture_combo, self.cursor_widget):
            pl.addWidget(w); w.setVisible(False)

        for btn, widget in zip(self.buttons, (self.cam_combo, mw, self.gesture_combo, self.cursor_widget)):
            btn.clicked.connect(lambda _,b=btn,w=widget:self.toggle_panel(b,w,content))

        # New Session button
        filler = QWidget(content); cl.addWidget(filler)
        new_btn = QPushButton("New session", filler); new_btn.setIcon(QIcon.fromTheme("document-new"))
        new_btn.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.8);color:black;padding:8px 12px;border-radius:6px;}"
            "QPushButton:hover{background:rgba(255,255,255,1.0);}"
        )
        new_btn.adjustSize(); new_btn.move(filler.width()-new_btn.width()-20, filler.height()-new_btn.height()-20); new_btn.show()
        filler.resizeEvent = lambda e: new_btn.move(filler.width()-new_btn.width()-20, filler.height()-new_btn.height()-20)
        new_btn.clicked.connect(self.on_new_session)

    def toggle_panel(self, btn, widget, content):
        if not btn.isChecked():
            self.panel.setVisible(False)
            return
        for other in self.buttons:
            if other is not btn:
                other.setChecked(False)
        for w in (self.cam_combo, self.mirror_slider.parent(), self.gesture_combo, self.cursor_widget):
            w.setVisible(False)
        widget.setVisible(True)
        pos = btn.mapTo(content, btn.rect().bottomLeft())
        self.panel.setFixedWidth(btn.width()); self.panel.adjustSize()
        self.panel.move(pos.x(), pos.y()+4); self.panel.setVisible(True)

    def on_sidebar_item_clicked(self, item):
        idx = self.sidebar.row(item)
        if idx == self.sidebar_idx:
            self.sidebar.clearSelection()
            self.sidebar_idx = -1
            self.sidebar_desc.setVisible(False)
            return
        self.sidebar_idx = idx
        key = item.text(); text, img = self.descriptions[key]
        self.desc_label.setText(text)
        self.img_label.setPixmap(QPixmap(img).scaledToWidth(184, Qt.SmoothTransformation))
        self.sidebar_desc.setVisible(True)

    def on_new_session(self):
        # Jeśli już działa, nic nie robimy
        if self.session_proc and self.session_proc.poll() is None:
            return
        # Zbieramy ustawienia
        cfg = {
            "camera_resolution": self.cam_combo.currentText(),
            "mirror_transparency": self.mirror_slider.value(),
            "gesture_recognition": self.gesture_combo.currentText(),
            "cursor_smoothing": {
                "epsilon": self.epsilon_slider.value(),
                "interpolation": self.interp_slider.value()
            }
        }
        # Zapis do JSON
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        # Uruchamiamy silnik
        self.session_proc = subprocess.Popen(
            [sys.executable, ENGINE_SCRIPT, CONFIG_FILE],
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
        )

    def closeEvent(self, event):
        if self.session_proc and self.session_proc.poll() is None:
            self.session_proc.terminate()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    fid = QFontDatabase.addApplicationFont("fonts/Quicksand/Quicksand-SemiBold.ttf")
    if fid >= 0:
        fam = QFontDatabase.applicationFontFamilies(fid)[0]
        app.setFont(QFont(fam, 11))
    w = MainWindow(); w.show()
    sys.exit(app.exec_())
