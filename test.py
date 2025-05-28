import sys
import cv2
import time
import math
import pyautogui as pg
import mediapipe as mp
from threading import Thread
from PyQt5 import QtCore, QtGui, QtWidgets

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

class HandGestureRecognizer:
    def __init__(self, stream):
        self.stream = stream
        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            model_complexity=1,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.prev_x, self.prev_y = 0, 0
        self.gesture_active = False
        self.holding_click = False
        self.gesture_start_time = None
        self.running = True
        self.gesture_frame_count = 0

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

            if results.multi_hand_landmarks:
                landmarks = results.multi_hand_landmarks[0].landmark

                # Smooth cursor
                ix, iy = self.smooth_cursor(landmarks[8], pg.size())
                pg.moveTo(ix, iy)

                # Gesture detection
                self.detect_gesture(landmarks)
            time.sleep(0.01)

    def smooth_cursor(self, index_tip, screen_size):
        x, y = int(index_tip.x * screen_size[0]), int(index_tip.y * screen_size[1])
        smooth_factor = 0.8
        new_x = self.prev_x + (x - self.prev_x) * smooth_factor
        new_y = self.prev_y + (y - self.prev_y) * smooth_factor

        if abs(new_x - self.prev_x) > 10 or abs(new_y - self.prev_y) > 10:
            pg.moveTo(new_x, new_y)
            self.prev_x, self.prev_y = new_x, new_y

        return new_x, new_y

    def detect_gesture(self, landmarks):
        index_tip = landmarks[8]
        thumb_tip = landmarks[4]
        dist = math.sqrt((index_tip.x - thumb_tip.x) ** 2 + (index_tip.y - thumb_tip.y) ** 2)
        gesture_threshold = 0.04

        if dist < gesture_threshold:
            self.gesture_frame_count += 1
            if self.gesture_frame_count >= 3:
                if not self.gesture_active:
                    self.gesture_active = True
                    self.gesture_start_time = time.time()
                else:
                    duration = time.time() - self.gesture_start_time
                    if duration > 0.5 and not self.holding_click:
                        pg.mouseDown()
                        self.holding_click = True
        else:
            if self.gesture_active:
                duration = time.time() - self.gesture_start_time
                if duration <= 0.5:
                    pg.click()
                elif self.holding_click:
                    pg.mouseUp()
                self.gesture_active = False
                self.holding_click = False
                self.gesture_frame_count = 0

    def stop(self):
        self.running = False

class TransparentOverlay(QtWidgets.QMainWindow):
    def __init__(self, stream):
        super().__init__()
        self.stream = stream

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.WindowTransparentForInput |
            QtCore.Qt.X11BypassWindowManagerHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.showFullScreen()

        self.label = QtWidgets.QLabel(self)
        self.label.setStyleSheet("background-color: transparent;")
        self.label.setAlignment(QtCore.Qt.AlignCenter)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label)
        container = QtWidgets.QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def update_frame(self):
        frame = self.stream.read()
        if frame is not None:
            frame = cv2.flip(frame, 1)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            img = QtGui.QImage(frame.data, w, h, ch * w, QtGui.QImage.Format_RGB888)
            pix = QtGui.QPixmap.fromImage(img).scaled(self.size(), QtCore.Qt.KeepAspectRatioByExpanding)
            self.label.setPixmap(pix)

def main():
    pg.FAILSAFE = True
    pg.PAUSE = 0

    stream = WebcamStream().start()
    recognizer = HandGestureRecognizer(stream)
    recognizer.start()

    app = QtWidgets.QApplication(sys.argv)
    overlay = TransparentOverlay(stream)
    app.aboutToQuit.connect(lambda: (stream.stop(), recognizer.stop()))
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
