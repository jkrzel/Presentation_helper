import sys, math
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QListWidget, QComboBox, QMainWindow
)
from PyQt5.QtGui import QFontDatabase, QFont, QPixmap, QIcon
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPainterPath, QBrush, QLinearGradient, QColor
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import QTimer

def gear_with_hole_path(center: QPointF,
                        radius: float,
                        teeth: int = 8,
                        tooth_depth: float = 0.2,
                        tooth_width: float = 0.6,
                        hole_ratio: float = 0.4,
                        corner_radius: float = None) -> QPainterPath:
    if corner_radius is None:
        corner_radius = radius * 0.05  # 5% zaokrąglenie

    path = QPainterPath()

    outer_r = radius
    inner_r = radius * (1 - tooth_depth)
    ang_step = 2 * math.pi / teeth
    half_tooth_ang = ang_step * tooth_width / 2

    def polar_to_point(r, angle):
        return QPointF(
            center.x() + r * math.cos(angle),
            center.y() + r * math.sin(angle)
        )

    for i in range(teeth):
        base_ang = i * ang_step
        a0 = base_ang - half_tooth_ang
        a1 = base_ang + half_tooth_ang

        # 4 punkty zęba
        p0 = polar_to_point(inner_r, a0)
        p1 = polar_to_point(outer_r, a0)
        p2 = polar_to_point(outer_r, a1)
        p3 = polar_to_point(inner_r, a1)

        if i == 0:
            path.moveTo(p0)
        else:
            path.lineTo(p0)

        # Zaokrąglenie do wierzchołka zęba
        if corner_radius > 0:
            path.lineTo(p1)
            path.quadTo(polar_to_point(outer_r + corner_radius, base_ang), p2)
        else:
            path.lineTo(p1)
            path.lineTo(p2)

        path.lineTo(p3)

    path.closeSubpath()

    # Dziura na środku
    hole_r = radius * hole_ratio
    path.addEllipse(center, hole_r, hole_r)
    path.setFillRule(Qt.OddEvenFill)

    return path




from PyQt5.QtCore import QTimer

class CogBackgroundWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rotation_angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)  # animacja ~33 klatek na sekundę

    def animate(self):
        self.rotation_angle = (self.rotation_angle + 1) % 360
        self.update()  # wymusza repaint widgetu

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # gradient tła
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0, QColor("#2e2e5c"))
        grad.setColorAt(1, QColor("#5c7bd1"))
        painter.fillRect(self.rect(), QBrush(grad))

        brush = QBrush(QColor(255, 255, 255, 7))

        gears = [
            (0.2, 0.3, 0.15),
            (0.5, 0.5, 0.35),
            (0.8, 0.2, 0.2),
            (0.8, 0.7, 0.25),
            (0.3, 0.75, 0.18),
            (0.6, 0.35, 0.12),
            (0.4, 0.2, 0.1),
        ]

        for i, (fx, fy, sz) in enumerate(gears):
            R = min(self.width(), self.height()) * sz
            center = QPointF(self.width() * fx, self.height() * fy)

            painter.save()
            # Różna prędkość obrotu dla każdej zębatki (możesz modyfikować)
            angle = self.rotation_angle * (1 + 0.3 * i)
            painter.translate(center)
            painter.rotate(angle)
            painter.translate(-center)

            gear_path = gear_with_hole_path(center, R / 2, teeth=8, tooth_depth=0.25, corner_radius=(R / 2) * 0.1)
            painter.setBrush(brush)
            painter.setPen(Qt.NoPen)
            painter.drawPath(gear_path)
            painter.restore()



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("logo.jpg"))
        self.setStyleSheet("QMainWindow { background-color: #1e1e3f; }")
        self.setWindowTitle("Presentation Helper")
        self.setMinimumSize(1300, 900)
        self.sidebar_selected_index = -1

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0,0,0,0)

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setFocusPolicy(Qt.NoFocus)
        self.sidebar.addItems(["left mouse","right mouse","resize","scroll","action circle"])
        self.sidebar.setFixedWidth(150)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background:transparent;
                border:none;
                color:white;
            }
            QListWidget::item {
                padding:8px;
                margin:4px;
                background:rgba(40,40,69,0.2);
                border-radius:6px;
            }
            QListWidget::item:hover {
                background:rgba(90,90,150,0.4);
            }
            QListWidget::item:selected {
                background:rgba(120,120,200,0.5);
            }
            QListWidget::item:focus {
                outline: none;
                border: none;
                background:rgba(120,120,200,0.5);  /* optionally repeat selected background */
            }
        """)

        for i in range(self.sidebar.count()):
            self.sidebar.item(i).setTextAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.sidebar)

        # Sidebar description + image (w szerszym panelu)
        self.sidebar_desc = QWidget()
        self.sidebar_desc.setStyleSheet("background:rgba(40,40,69,0.7); border-radius:8px;")
        sd_layout = QVBoxLayout(self.sidebar_desc)
        sd_layout.setContentsMargins(8,8,8,8)
        self.desc_label = QLabel()
        self.desc_label.setStyleSheet("color:white;")
        self.desc_label.setWordWrap(True)
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        sd_layout.addWidget(self.desc_label)
        sd_layout.addWidget(self.img_label)
        self.sidebar_desc.setVisible(False)
        self.sidebar_desc.setFixedWidth(200)  # 150 + 50
        main_layout.addWidget(self.sidebar_desc)

        self.descriptions = {
            "left mouse":    ("select and drag.",       "images/1.png"),
            "right mouse":   ("context menu.",          "images/2.png"),
            "resize":        ("change window size.",    "images/3.png"),
            "scroll":        ("wheel moves content.",   "images/4.png"),
            "action circle": ("special gesture.",       "images/5.png"),
        }
        self.sidebar.itemClicked.connect(self.on_sidebar_item_clicked)

        # Content area
        content = CogBackgroundWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16,16,16,16)
        main_layout.addWidget(content)

        # Topbar
        topbar = QWidget(content)
        topbar.setStyleSheet("background:rgba(30,30,63,0.8);")
        tl = QHBoxLayout(topbar)
        tl.setContentsMargins(10,4,10,4)
        tl.setSpacing(20)
        self.buttons = []
        for name in ("Camera Resolution", "Mirror Transparency",
                     "Gesture Recognition", "Cursor Motion Smoothing"):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(40,40,69,0.2);
                    color: white;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background: rgba(90,90,150,0.4);  /* <- jak w sidebarze */
                }
                QPushButton:checked {
                    background: rgba(120,120,200,0.5);  /* mocniejszy kolor dla kliknięcia */
                }
            """)

            tl.addWidget(btn)
            self.buttons.append(btn)
        tl.addStretch()
        content_layout.addWidget(topbar)

        # Settings panel
        self.panel = QWidget(content)
        self.panel.setStyleSheet("background:rgba(50,50,90,0.9); border-radius:10px;")
        pl = QVBoxLayout(self.panel)
        pl.setContentsMargins(12,12,12,12)
        self.panel.setVisible(False)

        # Widgets for panel
        self.cam_combo = QComboBox()
        self.cam_combo.addItems(["Low","Medium","High"])
        self.cam_combo.setStyleSheet("color:white;")

        self.mirror_widget = QWidget()
        mwl = QHBoxLayout(self.mirror_widget)
        mwl.setContentsMargins(0,0,0,0)
        self.m_sld = QSlider(Qt.Horizontal)
        self.m_sld.setRange(0,100)
        slider_style = """
            QSlider::groove:horizontal { border:1px solid #999; height:8px;
                                         background:rgba(40,40,69,0.2); border-radius:4px; }
            QSlider::handle:horizontal { background:#b3b3e3; border:1px solid #5c5c8a;
                                         width:14px; margin:-4px 0; border-radius:7px; }
        """
        self.m_sld.setStyleSheet(slider_style)
        self.m_val = QLabel("0")
        self.m_val.setStyleSheet("color:white; min-width:30px;")
        self.m_sld.valueChanged.connect(lambda v, lbl=self.m_val: lbl.setText(str(v)))
        mwl.addWidget(self.m_sld)
        mwl.addWidget(self.m_val)

        self.g_combo = QComboBox()
        self.g_combo.addItems(["Low","Medium","High"])
        self.g_combo.setStyleSheet("color:white;")

        # Cursor Motion Smoothing with labels centered above sliders
        self.cursor_widget = QWidget()
        cwl = QVBoxLayout(self.cursor_widget)
        cwl.setContentsMargins(0,0,0,0)
        for label_text in ("epsilon", "interpolation"):
            param_container = QWidget()
            pcl = QVBoxLayout(param_container)
            pcl.setContentsMargins(0,0,0,0)

            lbl = QLabel(label_text)
            lbl.setStyleSheet("color:white;")
            lbl.setAlignment(Qt.AlignCenter)
            pcl.addWidget(lbl)

            row = QWidget()
            rlayout = QHBoxLayout(row)
            rlayout.setContentsMargins(0,0,0,0)

            sld = QSlider(Qt.Horizontal)
            sld.setRange(0,100)
            sld.setStyleSheet(slider_style)

            val_lbl = QLabel("0")
            val_lbl.setStyleSheet("color:white; min-width:30px;")
            sld.valueChanged.connect(lambda v, l=val_lbl: l.setText(str(v)))

            rlayout.addWidget(sld)
            rlayout.addWidget(val_lbl)
            pcl.addWidget(row)

            cwl.addWidget(param_container)

        # Add widgets to panel and hide initially
        for w in (self.cam_combo, self.mirror_widget,
                  self.g_combo, self.cursor_widget):
            pl.addWidget(w)
            w.setVisible(False)

        # Connect topbar buttons
        for btn, widget in zip(self.buttons,
                               (self.cam_combo, self.mirror_widget,
                                self.g_combo, self.cursor_widget)):
            btn.clicked.connect(lambda _, b=btn, w=widget: self.toggle_panel(b, w, content))

        # Filler + new session
        filler = QWidget(content)
        filler.setSizePolicy(filler.sizePolicy().Expanding,
                             filler.sizePolicy().Expanding)
        content_layout.addWidget(filler)
        new_btn = QPushButton("New session", filler)
        new_btn.setIcon(QIcon.fromTheme("document-new"))
        new_btn.setStyleSheet("""
            QPushButton { background:rgba(255,255,255,0.8); color:black;
                          padding:8px 12px; border-radius:6px; }
            QPushButton:hover { background:rgba(255,255,255,1.0); }
        """)
        new_btn.adjustSize()
        new_btn.move(filler.width()-new_btn.width()-20,
                     filler.height()-new_btn.height()-20)
        new_btn.show()
        filler.resizeEvent = lambda e: new_btn.move(
            filler.width()-new_btn.width()-20,
            filler.height()-new_btn.height()-20
        )

    def toggle_panel(self, btn, widget, content):
        if not btn.isChecked():
            self.panel.setVisible(False)
            return
        for other in self.buttons:
            if other is not btn:
                other.setChecked(False)
        for w in (self.cam_combo, self.mirror_widget,
                  self.g_combo, self.cursor_widget):
            w.setVisible(False)
        widget.setVisible(True)
        pos = btn.mapTo(content, btn.rect().bottomLeft())
        self.panel.setFixedWidth(btn.width())
        self.panel.adjustSize()
        self.panel.move(pos.x(), pos.y() + 4)
        self.panel.raise_()
        self.panel.setVisible(True)

    def on_sidebar_item_clicked(self, item):
        index = self.sidebar.row(item)
        if index == self.sidebar_selected_index:
            # Odkliknięcie — ukryj opis i odznacz
            self.sidebar.clearSelection()
            self.sidebar_selected_index = -1
            self.sidebar_desc.setVisible(False)
            return

        # Kliknięcie nowego elementu
        self.sidebar_selected_index = index
        key = item.text()
        text, img_path = self.descriptions[key]
        self.desc_label.setText(text)
        pix = QPixmap(img_path)
        self.img_label.setPixmap(pix.scaledToWidth(200 - 16, Qt.SmoothTransformation))
        self.sidebar_desc.setVisible(True)

    def on_sidebar_changed(self, index):
        if index == self.sidebar_selected_index:
            # Odkliknięcie – ukryj opis i resetuj wybór
            self.sidebar.clearSelection()
            self.sidebar_selected_index = -1
            self.sidebar_desc.setVisible(False)
            return

        if index < 0:
            self.sidebar_desc.setVisible(False)
            self.sidebar_selected_index = -1
            return

        self.sidebar_selected_index = index
        key = self.sidebar.item(index).text()
        text, img_path = self.descriptions[key]
        self.desc_label.setText(text)
        pix = QPixmap(img_path)
        self.img_label.setPixmap(pix.scaledToWidth(200 - 16, Qt.SmoothTransformation))
        self.sidebar_desc.setVisible(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # ---  ŁADOWANIE CZCIONKI -------------
    font_id = QFontDatabase.addApplicationFont("fonts/Quicksand/Quicksand-SemiBold.ttf")
    if font_id < 0:
        print("❌ Nie udało się załadować czcionki")
    else:
        family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app.setFont(QFont(family, 11))  # 11 to domyślny rozmiar; zmień wg uznania
    # ---------------------------------------

    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
