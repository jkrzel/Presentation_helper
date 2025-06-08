import sys
import math
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton
from PyQt5.QtCore import Qt, QRectF, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QRegion, QFont


class PieButton(QPushButton):
    def __init__(self, parent, radius, inner_radius, start_angle_deg, span_deg, text, callback):
        super().__init__(text, parent)
        self.radius = radius
        self.inner_radius = inner_radius
        self.start_angle = start_angle_deg
        self.span = span_deg

        self.setFont(QFont("Arial", 10, QFont.Bold))
        self.setStyleSheet("background-color: transparent; border: none;")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(radius * 2, radius * 2)
        self.setMask(self._create_mask())
        self.clicked.connect(callback)

    def _create_mask(self):
        path = QPainterPath()
        path.moveTo(self.radius, self.radius)
        rect = QRectF(0, 0, self.radius * 2, self.radius * 2)
        path.arcTo(rect, self.start_angle, self.span)
        inner = QRectF(self.radius - self.inner_radius,
                       self.radius - self.inner_radius,
                       self.inner_radius * 2,
                       self.inner_radius * 2)
        path.arcTo(inner, self.start_angle + self.span, -self.span)
        path.closeSubpath()
        return QRegion(path.toFillPolygon().toPolygon())

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255,255,255,100))
        path = QPainterPath()
        path.moveTo(self.radius, self.radius)
        rect = QRectF(0,0,self.radius*2,self.radius*2)
        path.arcTo(rect, self.start_angle, self.span)
        inner = QRectF(self.radius-self.inner_radius,
                       self.radius-self.inner_radius,
                       self.inner_radius*2,
                       self.inner_radius*2)
        path.arcTo(inner, self.start_angle + self.span, -self.span)
        path.closeSubpath()
        p.drawPath(path)

        p.setPen(Qt.black)
        p.setFont(self.font())
        angle = math.radians(self.start_angle + self.span/2)
        dist = (self.radius + self.inner_radius)/2
        cx = self.radius + dist*math.cos(-angle)
        cy = self.radius + dist*math.sin(-angle)
        rect = QRectF(cx-70, cy-20, 140, 40)
        p.drawText(rect, Qt.AlignCenter, self.text())


class ActionCircle(QWidget):
    def __init__(self):
        super().__init__()
        # 75% z 700
        self.radius = int(700 * 0.75)
        self.inner_radius = self.radius - int(200 * 0.75)
        self.resize(self.radius*2, self.radius*2)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.buttons_info = [
            ("Exit", self._on_exit),
            ("Window Change", lambda: self._log("Window Change")),
            ("Laser Pointer", lambda: self._log("Laser Pointer"))
        ]
        self._create_buttons()

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.left() - self.radius, screen.bottom() - self.radius)

        # Ustawiamy początkową przezroczystość
        self.setWindowOpacity(0.0)
        self.show()
        QTimer.singleShot(50, self._fade_in)

    def _create_buttons(self):
        angles = [0,30,60]
        span = 30
        for i, (txt, cb) in enumerate(self.buttons_info):
            btn = PieButton(self, self.radius, self.inner_radius, angles[i], span, txt, cb)
            btn.move(self.radius - btn.width()//2, self.radius - btn.height()//2)
            btn.show()

    def _log(self, name):
        print(f"Clicked: {name}")

    def _on_exit(self):
        self._fade_out()

    def _fade_in(self):
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(1000)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        # Żeby obiekt nie został od razu skasowany:
        self._current_anim = anim

    def _fade_out(self):
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(800)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.finished.connect(self.close)
        anim.start()
        self._current_anim = anim

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(255,255,255,120))
        p.setPen(Qt.NoPen)
        path = QPainterPath()
        path.moveTo(self.radius, self.radius)
        rect = QRectF(0,0,self.radius*2,self.radius*2)
        path.arcTo(rect, -270, -90)
        path.lineTo(self.radius, self.radius)
        path.closeSubpath()
        p.drawPath(path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ActionCircle()
    sys.exit(app.exec_())
