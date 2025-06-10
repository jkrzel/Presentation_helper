import sys
import math
import tkinter as tk
from PIL import Image, ImageTk
import ctypes
import cv2
from threading import Thread
import mediapipe as mp
import pyautogui as pg
import win32gui
import win32con
import time

# PyQt5 imports for the circle overlay
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton
from PyQt5.QtCore import Qt, QRectF, QPropertyAnimation, QEasingCurve, QTimer, pyqtProperty, QParallelAnimationGroup
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QRegion, QFont

# Create a single QApplication for the Qt overlay
qt_app = QApplication(sys.argv)


class PieButton(QPushButton):
    """
    A circular (pie-slice) button for the ActionCircle menu.
    """

    def __init__(self, parent, radius, inner_radius, start_angle_deg, span_deg, text, callback):
        super().__init__(text, parent)
        self.radius = radius
        self.inner_radius = inner_radius
        self.start_angle = start_angle_deg
        self.span = span_deg
        self.hover = False  # Track hover state

        self.setFont(QFont("Arial", 10, QFont.Bold))
        # Remove default background styling that might conflict with our custom painting.
        self.setStyleSheet("background-color: transparent; border: none;")
        self.setMouseTracking(True)
        self.setFixedSize(radius * 2, radius * 2)
        self.setMask(self._create_mask())
        self.clicked.connect(callback)

    def enterEvent(self, event):
        self.hover = True
        self.update()  # trigger repaint
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover = False
        self.update()  # trigger repaint
        super().leaveEvent(event)

    def _create_mask(self):
        path = QPainterPath()
        path.moveTo(self.radius, self.radius)
        rect = QRectF(0, 0, self.radius * 2, self.radius * 2)
        path.arcTo(rect, self.start_angle, self.span)
        inner = QRectF(
            self.radius - self.inner_radius,
            self.radius - self.inner_radius,
            self.inner_radius * 2,
            self.inner_radius * 2
        )
        path.arcTo(inner, self.start_angle + self.span, -self.span)
        path.closeSubpath()
        return QRegion(path.toFillPolygon().toPolygon())

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        # Change the fill colour based on hover state
        if self.hover:
            p.setBrush(QColor(200, 200, 200, 150))
        else:
            p.setBrush(QColor(255, 255, 255, 100))
        path = QPainterPath()
        path.moveTo(self.radius, self.radius)
        rect = QRectF(0, 0, self.radius * 2, self.radius * 2)
        path.arcTo(rect, self.start_angle, self.span)
        inner = QRectF(
            self.radius - self.inner_radius,
            self.radius - self.inner_radius,
            self.inner_radius * 2,
            self.inner_radius * 2
        )
        path.arcTo(inner, self.start_angle + self.span, -self.span)
        path.closeSubpath()
        p.drawPath(path)

        p.setPen(Qt.black)
        p.setFont(self.font())
        angle = math.radians(self.start_angle + self.span / 2)
        dist = (self.radius + self.inner_radius) / 2
        cx = self.radius + dist * math.cos(-angle)
        cy = self.radius + dist * math.sin(-angle)
        text_rect = QRectF(cx - 70, cy - 20, 140, 40)
        p.drawText(text_rect, Qt.AlignCenter, self.text())


class ActionCircle(QWidget):
    """
    A semicircular menu that animates in/out and floats on top of other windows.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.radius = int(700 * 0.75)
        self.inner_radius = self.radius - int(200 * 0.75)
        self.resize(self.radius * 2, self.radius * 2)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._rotation = 0.0
        self.setWindowOpacity(0.0)

        # Define buttons with their callbacks
        self.buttons_info = [
            ("Exit", self._on_exit),
            ("Window Change", lambda: self._log("Window Change")),
            ("Laser Pointer", lambda: self._log("Laser Pointer"))
        ]
        self._create_buttons()

        # Adjust the position so the bottom-left of the widget aligns with the screen's bottom-left.
        screen_geom = QApplication.primaryScreen().availableGeometry()
        x = screen_geom.x()  # Typically 0
        y = screen_geom.height() - self.height()
        self.move(x, y)

        # Animate in after a short delay
        self.show()
        QTimer.singleShot(50, self._animate_in)

    def _create_buttons(self):
        angles = [0, 30, 60]
        span = 30
        for i, (txt, cb) in enumerate(self.buttons_info):
            btn = PieButton(
                self, self.radius, self.inner_radius,
                angles[i], span, txt, cb
            )
            btn.move(
                self.radius - btn.width() // 2,
                self.radius - btn.height() // 2
            )
            btn.show()

    def _log(self, name):
        print(f"Clicked: {name}")

    def _on_exit(self):
        self._animate_out()

    def _get_rotation(self):
        return self._rotation

    def _set_rotation(self, val):
        self._rotation = val
        self.update()

    rotation = pyqtProperty(float, _get_rotation, _set_rotation)

    def _animate_in(self):
        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(1000)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)

        rot = QPropertyAnimation(self, b"rotation", self)
        rot.setDuration(1000)
        rot.setStartValue(-30.0)
        rot.setEndValue(0.0)
        rot.setEasingCurve(QEasingCurve.OutBack)

        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(rot)
        group.start()
        self._current_anim = group

    def _animate_out(self):
        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(800)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.InCubic)

        rot = QPropertyAnimation(self, b"rotation", self)
        rot.setDuration(800)
        rot.setStartValue(0.0)
        rot.setEndValue(30.0)
        rot.setEasingCurve(QEasingCurve.InBack)

        fade.finished.connect(self.close)
        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(rot)
        group.start()
        self._current_anim = group

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cx = cy = self.radius
        p.translate(cx, cy)
        p.rotate(self._rotation)
        p.translate(-cx, -cy)

        p.setBrush(QColor(255, 255, 255, 120))
        p.setPen(Qt.NoPen)
        path = QPainterPath()
        path.moveTo(cx, cy)
        rect = QRectF(0, 0, self.radius * 2, self.radius * 2)
        # Draw a semicircular arc starting from -270 degrees over -90 degrees.
        path.arcTo(rect, -270, -90)
        path.lineTo(cx, cy)
        path.closeSubpath()
        p.drawPath(path)


class WebcamStream:
    def __init__(self, src=0, width=1280, height=720):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.ret, self.frame = self.cap.read()
        self.stopped = False

    def start(self):
        Thread(target=self.update, daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            self.ret, self.frame = self.cap.read()

    def read(self):
        return self.frame

    def stop(self):
        self.stopped = True
        self.cap.release()


def make_window_clickthrough(hwnd):
    WS_EX_LAYERED = 0x80000
    WS_EX_TRANSPARENT = 0x20
    GWL_EXSTYLE = -20
    LWA_ALPHA = 0x2
    styles = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(
        hwnd, GWL_EXSTYLE, styles | WS_EX_LAYERED | WS_EX_TRANSPARENT
    )
    ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, 40, LWA_ALPHA)


def resize_active_window(new_width, new_height):
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    win32gui.SetWindowPos(
        hwnd,
        None,
        left, top,
        new_width, new_height,
        win32con.SWP_NOZORDER | win32con.SWP_NOOWNERZORDER
    )


class HandGestureRecognizer:
    def __init__(self, stream):
        self.stream = stream
        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            model_complexity=1,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.prev_x, self.prev_y = 0, 0
        self.running = True
        self.cooldown_end = 0
        self.show_circle_flag = False

        # Click states
        self.left_frame_count = 0
        self.left_active = False
        self.left_holding = False
        self.left_start = None

        self.right_frame_count = 0
        self.right_active = False
        self.right_holding = False
        self.right_start = None

        # Resize states
        self.resizing = False
        self.initial_hand_x = None
        self.initial_hand_y = None
        self.initial_win_w = None
        self.initial_win_h = None

    def start(self):
        Thread(target=self.run, daemon=True).start()

    def run(self):
        while self.running:
            frame = self.stream.read()
            if frame is None:
                continue

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb)
            now = time.time()

            if results.multi_hand_landmarks:
                landmarks = results.multi_hand_landmarks
                if not self.resizing:
                    ix, iy = self.smooth_cursor(
                        landmarks[0].landmark[8], pg.size()
                    )
                    pg.moveTo(ix, iy)
                self.detect_gestures(landmarks, now)

            time.sleep(0.01)

    def smooth_cursor(self, index_tip, screen_size):
        x = int(index_tip.x * screen_size[0])
        y = int(index_tip.y * screen_size[1])
        smooth = 0.8
        new_x = self.prev_x + (x - self.prev_x) * smooth
        new_y = self.prev_y + (y - self.prev_y) * smooth
        self.prev_x, self.prev_y = new_x, new_y
        return new_x, new_y

    def detect_gestures(self, landmarks_list, now):
        # 1) BOTH-HANDS THUMBS-UP → set flag
        if len(landmarks_list) >= 2:
            thumbs_up = True
            for hand in landmarks_list[:2]:
                # Check if thumb is up (tip above middle joint)
                if not (hand.landmark[4].y < hand.landmark[2].y):
                    thumbs_up = False
                    break
                # Check other fingers are extended (tip above base)
                for finger_tip, finger_base in [(8, 6), (12, 10), (16, 14), (20, 18)]:
                    if hand.landmark[finger_tip].y < hand.landmark[finger_base].y:
                        thumbs_up = False
                        break

            if thumbs_up and now >= self.cooldown_end:
                self.show_circle_flag = True
                self.cooldown_end = now + 1.0
                return

        # 2) During cooldown, only resize
        if now < self.cooldown_end:
            if self.resizing:
                self.update_resize(landmarks_list[0].landmark)
            return

        # 3) LEFT-CLICK pinch + hold
        dist_mid = self.norm_dist(
            landmarks_list[0].landmark[12],
            landmarks_list[0].landmark[4]
        )
        if dist_mid < 0.04:
            self.left_frame_count += 1
            if self.left_frame_count >= 3:
                if not self.left_active:
                    self.left_active = True
                    self.left_start = now
                elif not self.left_holding and (now - self.left_start) > 0.5:
                    pg.mouseDown(button='left')
                    self.left_holding = True
            return
        else:
            if self.left_active:
                duration = now - self.left_start
                if duration <= 0.5:
                    pg.click(button='left')
                elif self.left_holding:
                    pg.mouseUp(button='left')
                self.left_active = False
                self.left_holding = False
            self.left_frame_count = 0

        # 4) RIGHT-CLICK pinch + hold
        dist_ring = self.norm_dist(
            landmarks_list[0].landmark[16],
            landmarks_list[0].landmark[4]
        )
        if dist_ring < 0.04:
            self.right_frame_count += 1
            if self.right_frame_count >= 3:
                if not self.right_active:
                    self.right_active = True
                    self.right_start = now
                elif not self.right_holding and (now - self.right_start) > 0.5:
                    pg.mouseDown(button='right')
                    self.right_holding = True
            return
        else:
            if self.right_active:
                duration = now - self.right_start
                if duration <= 0.5:
                    pg.click(button='right')
                elif self.right_holding:
                    pg.mouseUp(button='right')
                self.right_active = False
                self.right_holding = False
            self.right_frame_count = 0

    def norm_dist(self, p1, p2):
        return math.hypot(p1.x - p2.x, p1.y - p2.y)

    def stop(self):
        self.running = False


def main():
    pg.FAILSAFE = True
    pg.PAUSE = 0

    # Start webcam + recognizer
    stream = WebcamStream().start()
    recognizer = HandGestureRecognizer(stream)
    recognizer.start()

    # Build full-screen click-through Tk window
    window = tk.Tk()
    window.title("CameraOverlay")
    window.attributes('-fullscreen', True)
    window.attributes('-topmost', True)
    window.overrideredirect(True)
    window.configure(bg='black')

    label = tk.Label(window, bg='black')
    label.pack(fill="both", expand=True)

    window.update_idletasks()
    hwnd = win32gui.FindWindow(None, "CameraOverlay")
    make_window_clickthrough(hwnd)

    def update():
        # Update camera frame
        frame = stream.read()
        if frame is not None:
            frame = cv2.flip(frame, 1)
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (
                window.winfo_screenwidth(),
                window.winfo_screenheight()
            ))
            imgtk = ImageTk.PhotoImage(image=Image.fromarray(img))
            label.imgtk = imgtk
            label.configure(image=imgtk)

        # Pump Qt so any existing overlays animate
        qt_app.processEvents()

        # If thumbs-up was seen, create & force-show the circle
        if recognizer.show_circle_flag:
            circle = ActionCircle()
            circle.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            circle.show()
            circle.raise_()
            circle.activateWindow()

            # Also pin above all windows via Win32
            hwnd_qt = int(circle.winId())
            win32gui.SetWindowPos(
                hwnd_qt,
                win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
            )

            recognizer.show_circle_flag = False

        # Schedule next frame
        window.after(5, update)

    window.bind("<Escape>", lambda e: (
        stream.stop(), recognizer.stop(), window.destroy()
    ))
    update()
    window.mainloop()


if __name__ == "__main__":
    main()