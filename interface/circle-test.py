import sys
import math
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton
from PyQt5.QtCore import (
    Qt, QRectF, QPropertyAnimation, QEasingCurve,
    QTimer, pyqtProperty, QParallelAnimationGroup
)
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QRegion, QFont


class PieButton(QPushButton):
    def __init__(self, parent, radius, inner_radius,
                 start_angle_deg, span_deg, text, callback):
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
        rect = QRectF(0, 0, self.radius*2, self.radius*2)
        path.arcTo(rect, self.start_angle, self.span)
        inner = QRectF(self.radius-self.inner_radius,
                       self.radius-self.inner_radius,
                       self.inner_radius*2,
                       self.inner_radius*2)
        path.arcTo(inner, self.start_angle + self.span, -self.span)
        path.closeSubpath()
        return QRegion(path.toFillPolygon().toPolygon())

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 100))
        path = QPainterPath()
        path.moveTo(self.radius, self.radius)
        rect = QRectF(0, 0, self.radius*2, self.radius*2)
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
        self.radius = int(700 * 0.75)
        self.inner_radius = self.radius - int(200 * 0.75)
        self.resize(self.radius*2, self.radius*2)
        self.setWindowFlags(Qt.FramelessWindowHint |
                            Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # początkowe właściwości
        self._rotation = 0.0
        self.setWindowOpacity(0.0)

        self.buttons_info = [
            ("Exit", self._on_exit),
            ("Window Change", lambda: self._log("Window Change")),
            ("Laser Pointer", lambda: self._log("Laser Pointer"))
        ]
        self._create_buttons()

        geom = QApplication.primaryScreen().availableGeometry()
        self.move(geom.left() - self.radius, geom.bottom() - self.radius)

        # pokaz+animuj
        self.show()
        QTimer.singleShot(50, self._animate_in)

    def _create_buttons(self):
        angles = [0, 30, 60]
        span = 30
        for i, (txt, cb) in enumerate(self.buttons_info):
            btn = PieButton(self, self.radius, self.inner_radius,
                            angles[i], span, txt, cb)
            btn.move(self.radius - btn.width()//2,
                     self.radius - btn.height()//2)
            btn.show()

    def _log(self, name):
        print(f"Clicked: {name}")

    def _on_exit(self):
        self._animate_out()

    # --- właściwość rotation ---
    def _get_rotation(self):
        return self._rotation
    def _set_rotation(self, val):
        self._rotation = val
        self.update()
    rotation = pyqtProperty(float, _get_rotation, _set_rotation)

    def _animate_in(self):
        # fade-in
        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(1000)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)
        # rotate-in z -30° do 0°
        rot = QPropertyAnimation(self, b"rotation", self)
        rot.setDuration(1000)
        rot.setStartValue(-30.0)
        rot.setEndValue(0.0)
        rot.setEasingCurve(QEasingCurve.OutBack)
        # uruchom równolegle
        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(rot)
        group.start()
        self._current_anim = group

    def _animate_out(self):
        # fade-out
        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(800)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.InCubic)
        # rotate-out z 0° do +30°
        rot = QPropertyAnimation(self, b"rotation", self)
        rot.setDuration(800)
        rot.setStartValue(0.0)
        rot.setEndValue(30.0)
        rot.setEasingCurve(QEasingCurve.InBack)
        # gdy skończone, zamknij
        fade.finished.connect(self.close)
        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(rot)
        group.start()
        self._current_anim = group

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # zastosuj rotację wokół środka
        cx = cy = self.radius
        p.translate(cx, cy)
        p.rotate(self._rotation)
        p.translate(-cx, -cy)
        # tło
        p.setBrush(QColor(255,255,255,120))
        p.setPen(Qt.NoPen)
        path = QPainterPath()
        path.moveTo(cx, cy)
        rect = QRectF(0,0,self.radius*2,self.radius*2)
        path.arcTo(rect, -270, -90)
        path.lineTo(cx, cy)
        path.closeSubpath()
        p.drawPath(path)

    def close(self):
        super().close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ActionCircle()
    sys.exit(app.exec_())
