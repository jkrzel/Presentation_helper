import sys, math
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QListWidget, QGraphicsOpacityEffect
)
from PyQt5.QtGui import QFontDatabase, QFont, QPixmap, QIcon, QPainter, QPainterPath, QBrush, QLinearGradient, QColor
from PyQt5.QtCore import Qt, QPointF, QTimer
from PyQt5.QtMultimedia import QCamera, QCameraInfo
from PyQt5.QtMultimediaWidgets import QCameraViewfinder

# Funkcja tworząca kształt zębatki
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
    outer = radius
    inner = radius * (1 - tooth_depth)
    step = 2 * math.pi / teeth
    half = step * tooth_width / 2
    def p(r, a): return QPointF(center.x() + r * math.cos(a), center.y() + r * math.sin(a))
    for i in range(teeth):
        ang = i * step
        a0, a1 = ang - half, ang + half
        pts = [p(inner, a0), p(outer, a0), p(outer, a1), p(inner, a1)]
        if i == 0:
            path.moveTo(pts[0])
        else:
            path.lineTo(pts[0])
        if corner_radius > 0:
            path.lineTo(pts[1]); path.quadTo(p(outer + corner_radius, ang), pts[2])
        else:
            path.lineTo(pts[1]); path.lineTo(pts[2])
        path.lineTo(pts[3])
    path.closeSubpath()
    hole = radius * hole_ratio
    path.addEllipse(center, hole, hole)
    path.setFillRule(Qt.OddEvenFill)
    return path

# Tło z obracającymi się zębatkami
class CogBackgroundWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.angle = 0
        timer = QTimer(self)
        timer.timeout.connect(self.animate)
        timer.start(30)

    def animate(self):
        self.angle = (self.angle + 1) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0, QColor('#2e2e5c'))
        grad.setColorAt(1, QColor('#5c7bd1'))
        painter.fillRect(self.rect(), QBrush(grad))
        brush = QBrush(QColor(255,255,255,7))
        gears = [(0.2,0.3,0.15),(0.5,0.5,0.35),(0.8,0.2,0.2),(0.8,0.7,0.25),(0.3,0.75,0.18),(0.6,0.35,0.12),(0.4,0.2,0.1)]
        for i,(fx,fy,sz) in enumerate(gears):
            R = min(self.width(), self.height())*sz
            c = QPointF(self.width()*fx, self.height()*fy)
            painter.save()
            painter.translate(c); painter.rotate(self.angle*(1+0.3*i)); painter.translate(-c)
            path = gear_with_hole_path(c, R/2)
            painter.setBrush(brush)
            painter.setPen(Qt.NoPen)
            painter.drawPath(path)
            painter.restore()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Presentation Helper')
        self.resize(1300,900)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0,0,0,0)

        # Sidebar
        self.sidebar = QListWidget()
        for t in ['left mouse','right mouse','resize','scroll','action circle']:
            self.sidebar.addItem(t)
        self.sidebar.setFixedWidth(150)
        self.sidebar.setStyleSheet(
            'QListWidget{background:transparent;color:white;border:none;}'
            'QListWidget::item{padding:8px;margin:4px;background:rgba(40,40,69,0.2);border-radius:6px;}'
            'QListWidget::item:hover{background:rgba(90,90,150,0.4);}'
            'QListWidget::item:selected{background:rgba(120,120,200,0.5);}'
        )
        for i in range(self.sidebar.count()):
            self.sidebar.item(i).setTextAlignment(Qt.AlignCenter)
        layout.addWidget(self.sidebar)

        # Sidebar desc
        self.sidebar_desc = QWidget()
        self.sidebar_desc.setFixedWidth(200)
        sd = QVBoxLayout(self.sidebar_desc)
        sd.setContentsMargins(8,8,8,8)
        self.desc_label = QLabel()
        self.desc_label.setStyleSheet('color:white;')
        self.desc_label.setWordWrap(True)
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        sd.addWidget(self.desc_label)
        sd.addWidget(self.img_label)
        self.sidebar_desc.setVisible(False)
        layout.addWidget(self.sidebar_desc)

        # Content
        self.content = CogBackgroundWidget()
        content_l = QVBoxLayout(self.content)
        content_l.setContentsMargins(16,16,16,16)
        layout.addWidget(self.content)

        # Topbar
        top = QWidget(self.content)
        top.setStyleSheet('background:rgba(30,30,63,0.8);')
        tb = QHBoxLayout(top)
        tb.setContentsMargins(10,4,10,4)
        tb.setSpacing(20)
        self.buttons = []
        for name in ['Camera Resolution','Mirror Transparency','Gesture Recognition','Cursor Motion Smoothing']:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setStyleSheet(
                'QPushButton{background:rgba(40,40,69,0.2);color:white;border-radius:6px;padding:4px 8px;}'
                'QPushButton:hover{background:rgba(90,90,150,0.4);}'
                'QPushButton:checked{background:rgba(120,120,200,0.5);}'
            )
            tb.addWidget(btn)
            self.buttons.append(btn)
        tb.addStretch()
        content_l.addWidget(top)

        # Slider panel
        self.slider_panel = QWidget(self.content)
        self.slider_panel.setStyleSheet('background:rgba(50,50,90,0.9);border-radius:10px;')
        sp = QHBoxLayout(self.slider_panel)
        sp.setContentsMargins(12,12,12,12)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0,100)
        self.slider.setValue(0)
        self.label_val = QLabel('0')
        self.label_val.setStyleSheet('color:white;min-width:30px;')
        self.slider.valueChanged.connect(lambda v: self.label_val.setText(str(v)))
        self.slider.valueChanged.connect(self.update_mirror_opacity)
        sp.addWidget(self.slider)
        sp.addWidget(self.label_val)
        self.slider_panel.hide()

        # Camera view
        self.camera_view = QCameraViewfinder(self.content)
        self.camera_view.setFixedSize(400,300)
        self.camera_view.setStyleSheet('border:2px solid white;')
        self.camera_view.hide()
        cam = QCameraInfo.defaultCamera()
        if not cam.isNull():
            self.camera = QCamera(cam)
            self.camera.setViewfinder(self.camera_view)
            self.camera.start()
        self.effect = QGraphicsOpacityEffect(self.camera_view)
        self.camera_view.setGraphicsEffect(self.effect)
        self.effect.setOpacity(1.0)

        # Connect buttons
        for btn in self.buttons:
            btn.clicked.connect(lambda _, b=btn: self.on_top_button(b))

    def on_top_button(self, btn):
        # reset other
        for b in self.buttons:
            if b is not btn:
                b.setChecked(False)
        self.camera_view.hide()
        self.slider_panel.hide()
        if not btn.isChecked():
            return
        if btn.text() == 'Mirror Transparency':
            # position slider panel under button
            pos = btn.mapTo(self.content, btn.rect().bottomLeft())
            self.slider_panel.adjustSize()
            self.slider_panel.move(pos.x(), pos.y() + 4)
            self.slider_panel.show()
            # position camera view center
            cw, ch = self.content.width(), self.content.height()
            w, h = self.camera_view.width(), self.camera_view.height()
            self.camera_view.move((cw - w)//2, (ch - h)//2)
            self.camera_view.show()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # reposition camera view
        if self.camera_view.isVisible():
            cw, ch = self.content.width(), self.content.height()
            w, h = self.camera_view.width(), self.camera_view.height()
            self.camera_view.move((cw - w)//2, (ch - h)//2)
        # reposition slider panel
        if self.slider_panel.isVisible():
            for btn in self.buttons:
                if btn.isChecked() and btn.text() == 'Mirror Transparency':
                    pos = btn.mapTo(self.content, btn.rect().bottomLeft())
                    self.slider_panel.move(pos.x(), pos.y() + 4)

    def update_mirror_opacity(self, val):
        self.effect.setOpacity(1 - val / 100.0)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    fid = QFontDatabase.addApplicationFont('fonts/Quicksand/Quicksand-SemiBold.ttf')
    if fid >= 0:
        fam = QFontDatabase.applicationFontFamilies(fid)[0]
        app.setFont(QFont(fam, 11))
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
