import tkinter as tk
from PIL import Image, ImageTk
import ctypes
import cv2
from threading import Thread
import mediapipe as mp
import pyautogui as pg
import win32gui

class WebcamStream:
    def __init__(self, src=0, width=640, height=360):
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
    ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, 60, LWA_ALPHA)

def get_index_finger_coordinates(frame, hands):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)
    if results.multi_hand_landmarks:
        lm = results.multi_hand_landmarks[0].landmark[8]
        w, h = pg.size()
        return int(lm.x * w), int(lm.y * h)
    return None

def main():
    pg.FAILSAFE = True
    pg.PAUSE = 0
    stream = WebcamStream().start()
    hands = mp.solutions.hands.Hands(
        static_image_mode=False,
        model_complexity=1,
        max_num_hands=1,
        min_detection_confidence=0.3,
        min_tracking_confidence=0.2
    )

    prev_x, prev_y = 0, 0
    smooth = 0.8
    eps = 10

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
        nonlocal prev_x, prev_y
        frame = stream.read()
        if frame is not None:
            frame = cv2.flip(frame, 1)

            coords = get_index_finger_coordinates(frame, hands)
            if coords:
                x, y = coords
                ix = prev_x + (x - prev_x) * smooth
                iy = prev_y + (y - prev_y) * smooth
                if abs(ix - prev_x) > eps or abs(iy - prev_y) > eps:
                    pg.moveTo(ix, iy)
                    prev_x, prev_y = ix, iy

            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
            image = cv2.resize(image, (screen_width, screen_height))

            imgtk = ImageTk.PhotoImage(image=Image.fromarray(image))
            label.imgtk = imgtk
            label.configure(image=imgtk)

        window.after(10, update)

    window.bind("<Escape>", lambda e: (stream.stop(), window.destroy()))
    update()
    window.mainloop()

if __name__ == "__main__":
    main()


