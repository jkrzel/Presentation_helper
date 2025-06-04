import tkinter as tk
from PIL import Image, ImageTk
import ctypes
import cv2
from threading import Thread
import mediapipe as mp
import pyautogui as pg
import win32gui
import win32con
import math
import time

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
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, styles | WS_EX_LAYERED | WS_EX_TRANSPARENT)
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

        self.left_frame_count = 0
        self.left_active = False
        self.left_holding = False
        self.left_start = None

        self.right_frame_count = 0
        self.right_active = False
        self.right_holding = False
        self.right_start = None

        self.toggle_frame_count = 0
        self.toggle_active = False
        self.toggle_start = None

        self.resizing = False
        self.initial_hand_y = None
        self.initial_hand_x = None
        self.initial_win_w = None
        self.initial_win_h = None

        self.cooldown_end = 0
        self.running = True

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
                landmarks_list = results.multi_hand_landmarks
                if not self.resizing:
                    first = landmarks_list[0]
                    ix, iy = self.smooth_cursor(first.landmark[8], pg.size())
                    pg.moveTo(ix, iy)
                self.detect_gestures(landmarks_list, now)
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

    def detect_gestures(self, landmarks_list, now):
        if now < self.cooldown_end:
            if self.resizing:
                self.update_resize(landmarks_list[0].landmark)
            return

        # Toggle-resize: thumbs-up on both hands
        if len(landmarks_list) >= 2:
            thumbs = []
            for hand in landmarks_list[:2]:
                lm = hand.landmark
                thumb_tip = lm[4]
                thumb_mcp = lm[2]
                index_tip = lm[8]
                index_pip = lm[6]
                middle_tip = lm[12]
                middle_pip = lm[10]
                ring_tip = lm[16]
                ring_pip = lm[14]
                pinky_tip = lm[20]
                pinky_pip = lm[18]
                thumb_up = (
                    thumb_tip.y < thumb_mcp.y and
                    index_tip.y > index_pip.y and
                    middle_tip.y > middle_pip.y and
                    ring_tip.y > ring_pip.y and
                    pinky_tip.y > pinky_pip.y
                )
                thumbs.append(thumb_up)
            if all(thumbs):
                self.toggle_frame_count += 1
                if self.toggle_frame_count >= 3:
                    if not self.toggle_active:
                        self.toggle_active = True
                        self.toggle_start = time.time()
                        if not self.resizing:
                            self.start_resize(landmarks_list[0].landmark)
                        else:
                            self.end_resize()
                        self.cooldown_end = time.time() + 4
                return
            else:
                self.toggle_frame_count = 0
                self.toggle_active = False

        # While resizing, update size
        if self.resizing:
            self.update_resize(landmarks_list[0].landmark)
            return

        # Left-click: thumb + middle finger of first hand
        lm0 = landmarks_list[0].landmark
        thumb_tip = lm0[4]
        middle_tip = lm0[12]
        dist_mid_thumb = self.norm_dist(middle_tip, thumb_tip)
        threshold = 0.04
        if dist_mid_thumb < threshold:
            self.left_frame_count += 1
            if self.left_frame_count >= 3:
                if not self.left_active:
                    self.left_active = True
                    self.left_start = time.time()
                else:
                    duration = time.time() - self.left_start
                    if duration > 0.5 and not self.left_holding:
                        pg.mouseDown(button='left')
                        self.left_holding = True
        else:
            if self.left_active:
                duration = time.time() - self.left_start
                if duration <= 0.5:
                    pg.click(button='left')
                elif self.left_holding:
                    pg.mouseUp(button='left')
                self.left_active = False
                self.left_holding = False
                self.left_frame_count = 0

        # Right-click: thumb + ring finger of first hand
        ring_tip = lm0[16]
        dist_ring_thumb = self.norm_dist(ring_tip, thumb_tip)
        if dist_ring_thumb < threshold:
            self.right_frame_count += 1
            if self.right_frame_count >= 3:
                if not self.right_active:
                    self.right_active = True
                    self.right_start = time.time()
                else:
                    duration = time.time() - self.right_start
                    if duration > 0.5 and not self.right_holding:
                        pg.mouseDown(button='right')
                        self.right_holding = True
        else:
            if self.right_active:
                duration = time.time() - self.right_start
                if duration <= 0.5:
                    pg.click(button='right')
                elif self.right_holding:
                    pg.mouseUp(button='right')
                self.right_active = False
                self.right_holding = False
                self.right_frame_count = 0

        # Resize-ish: index+middle extended, others closed
        wrist = lm0[0]
        index_tip = lm0[8]
        middle_tip = lm0[12]
        ring_tip = lm0[16]
        pinky_tip = lm0[20]
        high_threshold = 0.1
        low_threshold = 0.05
        dist_index_wrist = self.norm_dist(index_tip, wrist)
        dist_middle_wrist = self.norm_dist(middle_tip, wrist)
        dist_ring_wrist = self.norm_dist(ring_tip, wrist)
        dist_pinky_wrist = self.norm_dist(pinky_tip, wrist)
        if dist_index_wrist > high_threshold and dist_middle_wrist > high_threshold and dist_ring_wrist < low_threshold and dist_pinky_wrist < low_threshold:
            print("resize")

        # action_circle: all fingers extended
        dist_ring_wrist2 = self.norm_dist(ring_tip, wrist)
        dist_pinky_wrist2 = self.norm_dist(pinky_tip, wrist)
        dist_thumb_wrist = self.norm_dist(thumb_tip, wrist)
        if (
            dist_index_wrist > high_threshold and
            dist_middle_wrist > high_threshold and
            dist_ring_wrist2 > high_threshold and
            dist_pinky_wrist2 > high_threshold and
            dist_thumb_wrist > high_threshold
        ):
            print("action_circle")

    def start_resize(self, lm):
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return
        rect = win32gui.GetWindowRect(hwnd)
        self.initial_win_w = rect[2] - rect[0]
        self.initial_win_h = rect[3] - rect[1]
        self.initial_hand_y = lm[8].y
        self.initial_hand_x = lm[8].x
        self.resizing = True

    def update_resize(self, lm):
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd or self.initial_win_w is None:
            return
        current_hand_y = lm[8].y
        current_hand_x = lm[8].x
        dy = self.initial_hand_y - current_hand_y
        dx = current_hand_x - self.initial_hand_x
        scale_factor = 2.0
        new_w = max(100, int(self.initial_win_w + dx * self.initial_win_w * scale_factor))
        new_h = max(100, int(self.initial_win_h + dy * self.initial_win_h * scale_factor))
        resize_active_window(new_w, new_h)

    def end_resize(self):
        self.resizing = False
        self.initial_win_w = None
        self.initial_win_h = None
        self.initial_hand_y = None
        self.initial_hand_x = None

    def norm_dist(self, p1, p2):
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
