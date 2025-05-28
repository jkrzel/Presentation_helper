import tkinter as tk
from PIL import Image, ImageTk
import ctypes
import cv2
from threading import Thread
import mediapipe as mp
import pyautogui as pg
import win32gui
import math
import time

class WebcamStream:
    def __init__(self, src=0, width=1280, height=720):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.ret, self.frame = self.cap.read()
        #self.cap.set(cv2.CAP_PROP_FPS, 60)
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
    # jak wcześniej...
    WS_EX_LAYERED = 0x80000
    WS_EX_TRANSPARENT = 0x20
    GWL_EXSTYLE = -20
    LWA_ALPHA = 0x2

    styles = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, styles | WS_EX_LAYERED | WS_EX_TRANSPARENT)
    ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, 40, LWA_ALPHA)


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
                h, w, _ = frame.shape
                landmarks = results.multi_hand_landmarks[0].landmark

                # Wygładzanie pozycji
                ix, iy = self.smooth_cursor(landmarks[8], pg.size())
                pg.moveTo(ix, iy)

                # Analiza gestu
                self.detect_gesture(landmarks)
            time.sleep(0.01)

    def smooth_cursor(self, index_tip, screen_size):
        x, y = int(index_tip.x * screen_size[0]), int(index_tip.y * screen_size[1])
        smooth_factor = 0.8
        new_x = self.prev_x + (x - self.prev_x) * smooth_factor
        new_y = self.prev_y + (y - self.prev_y) * smooth_factor

        # Dodatkowe filtrowanie epsilonem
        if abs(new_x - self.prev_x) > 10 or abs(new_y - self.prev_y) > 10:
            pg.moveTo(new_x, new_y)
            self.prev_x, self.prev_y = new_x, new_y

        return new_x, new_y

    def detect_gesture(self, landmarks):
        index_tip = landmarks[8]
        thumb_tip = landmarks[4]

        dist = self.normalized_distance(index_tip, thumb_tip)
        gesture_threshold = 0.04  # 3% ekranu

        if dist < gesture_threshold:
            self.gesture_frame_count += 1
            if self.gesture_frame_count >= 3:  # gest stabilny przez 3 klatki
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

    def normalized_distance(self, p1, p2):
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

    def stop(self):
        self.running = False


def main():
    pg.FAILSAFE = True
    pg.PAUSE = 0

    stream = WebcamStream().start()
    recognizer = HandGestureRecognizer(stream)
    recognizer.start()

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
        frame = stream.read()
        if frame is not None:
            frame = cv2.flip(frame, 1)
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = cv2.resize(image, (window.winfo_screenwidth(), window.winfo_screenheight()))
            imgtk = ImageTk.PhotoImage(image=Image.fromarray(image))
            label.imgtk = imgtk
            label.configure(image=imgtk)
        window.after(5, update)

    window.bind("<Escape>", lambda e: (stream.stop(), recognizer.stop(), window.destroy()))
    update()
    window.mainloop()

if __name__ == "__main__":
    main()

