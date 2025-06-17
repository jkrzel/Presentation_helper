import sys
import math
import tkinter as tk
import json
from PIL import Image, ImageTk
import ctypes
import cv2
from threading import Thread
import mediapipe as mp
import pyautogui as pg
import win32gui
import win32con
import time

# PyQt5 imports for completeness (we no longer show the ActionCircle)
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Initialize a Qt app so nothing breaks if someone still instantiates the circle
qt_app = QApplication(sys.argv)


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


def make_window_clickthrough(hwnd, alpha):
    WS_EX_LAYERED     = 0x80000
    WS_EX_TRANSPARENT = 0x20
    GWL_EXSTYLE       = -20
    LWA_ALPHA         = 0x2
    styles = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(
        hwnd, GWL_EXSTYLE, styles | WS_EX_LAYERED | WS_EX_TRANSPARENT
    )
    ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha, LWA_ALPHA)


def resize_active_window(new_width, new_height):
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    win32gui.SetWindowPos(
        hwnd, None,
        left, top,
        new_width, new_height,
        win32con.SWP_NOZORDER | win32con.SWP_NOOWNERZORDER
    )


class HandGestureRecognizer:
    def __init__(self, stream):
        self.stream = stream

        # Default — overridden in main()
        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            model_complexity=1,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )

        # Cursor smoothing state
        self.prev_x, self.prev_y = 0, 0
        self.smooth_factor = 0.8

        # Thread control & gesture flags
        self.running = True
        self.cooldown_end = 0
        self.show_resize_flag = False

        # Left-click pinch state
        self.left_frame_count = 0
        self.left_active = False
        self.left_holding = False
        self.left_start = None

        # Right-click pinch state
        self.right_frame_count = 0
        self.right_active = False
        self.right_holding = False
        self.right_start = None

        # Drag‑resize state
        self.resizing = False
        self.initial_hand_x = None
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
                lm = results.multi_hand_landmarks
                # move cursor
                if not self.resizing:
                    ix, iy = self.smooth_cursor(lm[0].landmark[8], pg.size())
                    pg.moveTo(ix, iy)
                # detect all gestures
                self.detect_gestures(lm, now)

            time.sleep(0.01)

    def smooth_cursor(self, tip, screen_size):
        x = int(tip.x * screen_size[0])
        y = int(tip.y * screen_size[1])
        nx = self.prev_x + (x - self.prev_x) * self.smooth_factor
        ny = self.prev_y + (y - self.prev_y) * self.smooth_factor
        self.prev_x, self.prev_y = nx, ny
        return nx, ny

    def detect_gestures(self, hands, now):
        # ── 1) TWO‑THUMBS‑UP → maximize/restore ─────────────────────────────
        if len(hands) >= 2:
            thumbs_up = True
            for h in hands[:2]:
                # thumb tip above thumb MCP
                if h.landmark[4].y >= h.landmark[2].y:
                    thumbs_up = False
                    break
                # other fingers folded
                for tip, base in [(8, 6), (12, 10), (16, 14), (20, 18)]:
                    if h.landmark[tip].y < h.landmark[base].y:
                        thumbs_up = False
                        break
            if thumbs_up and now >= self.cooldown_end:
                self.show_resize_flag = True
                self.cooldown_end = now + 1.0
                # reset any ongoing drag‑resize
                self.resizing = False
                return

        # ── 2) DRAG‑RESIZE (during cooldown if started) ──────────────────────
        if now < self.cooldown_end and self.resizing:
            # use first hand to drag-resize
            lm = hands[0].landmark[8]
            dx = lm.x - self.initial_hand_x
            new_w = int(self.initial_win_w * (1 + dx))
            new_h = int(self.initial_win_h * (1 + dx))
            resize_active_window(new_w, new_h)
            return

        # ── 3) LEFT‑CLICK PINCH ───────────────────────────────────────────────
        d_mid = self.norm_dist(hands[0].landmark[12], hands[0].landmark[4])
        if d_mid < 0.04:
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
                dur = now - self.left_start
                if dur <= 0.5:
                    pg.click(button='left')
                elif self.left_holding:
                    pg.mouseUp(button='left')
                self.left_active = False
                self.left_holding = False
            self.left_frame_count = 0

        # ── 4) RIGHT‑CLICK PINCH ──────────────────────────────────────────────
        d_ring = self.norm_dist(hands[0].landmark[16], hands[0].landmark[4])
        if d_ring < 0.04:
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
                dur = now - self.right_start
                if dur <= 0.5:
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
    # — 1) Load JSON config —
    cfg = {}
    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            print(f"Failed to load config: {e}")

    # — 2) Camera resolution map —
    res_map = {"Low": (640, 480), "Medium": (1280, 720), "High": (1920, 1080)}
    cam_w, cam_h = res_map.get(cfg.get("camera_resolution"), (1280, 720))

    # — 2b) Gesture-recognition → confidences —
    gr = cfg.get("gesture_recognition", "Medium")
    det_c, track_c = {"Low": (0.3, 0.3), "Medium": (0.7, 0.7), "High": (0.9, 0.9)}[gr]

    # — 3) Cursor smoothing factor —
    interp = cfg.get("cursor_smoothing", {}).get("interpolation", 80) / 100.0

    # — 4) Mirror transparency → window alpha —
    alpha = int(cfg.get("mirror_transparency", 40) * 2.55)

    pg.FAILSAFE = True
    pg.PAUSE = 0

    # start camera & recognizer
    stream = WebcamStream(0, cam_w, cam_h).start()
    recognizer = HandGestureRecognizer(stream)
    recognizer.smooth_factor = interp
    # override MediaPipe confidences
    recognizer.hands = mp.solutions.hands.Hands(
        static_image_mode=False,
        model_complexity=1,
        max_num_hands=2,
        min_detection_confidence=det_c,
        min_tracking_confidence=track_c
    )
    recognizer.start()

    # build full-screen click-through camera window
    window = tk.Tk()
    window.title("CameraOverlay")
    window.attributes('-fullscreen', True)
    window.attributes('-topmost', True)
    window.overrideredirect(True)
    window.configure(bg='black')

    label = tk.Label(window, bg='black')
    label.pack(fill="both", expand=True)

    window.update_idletasks()
    hwnd_cam = win32gui.FindWindow(None, "CameraOverlay")
    make_window_clickthrough(hwnd_cam, alpha)

    def update_loop():
        frame = stream.read()
        if frame is not None:
            img = cv2.flip(frame, 1)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (window.winfo_screenwidth(),
                                   window.winfo_screenheight()))
            imgtk = ImageTk.PhotoImage(image=Image.fromarray(img))
            label.imgtk = imgtk
            label.configure(image=imgtk)

        # process Qt events (for any unused overlays)
        qt_app.processEvents()

        # ── Handle two-thumbs-up maximize/restore ──────────────────────────
        if recognizer.show_resize_flag:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd != hwnd_cam:
                placement = win32gui.GetWindowPlacement(hwnd)[1]
                # if already maximized
                if placement == win32con.SW_SHOWMAXIMIZED:
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                else:
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            recognizer.show_resize_flag = False

        window.after(5, update_loop)

    window.bind("<Escape>", lambda e: (stream.stop(), recognizer.stop(), window.destroy()))
    update_loop()
    window.mainloop()


if __name__ == "__main__":
    main()
