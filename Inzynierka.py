import cv2
import mediapipe as mp
import pyautogui as pg
import time
from threading import Thread

class WebcamStream:
    def __init__(self, src=0, width=640, height=480):
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
        model_complexity=0,
        max_num_hands=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    prev_x, prev_y = 0, 0
    smooth = 0.8
    eps = 10

    while True:
        frame = stream.read()
        if frame is None:
            continue
        frame = cv2.flip(frame, 1)
        coords = get_index_finger_coordinates(frame, hands)
        if coords:
            x, y = coords
            ix = prev_x + (x - prev_x) * smooth
            iy = prev_y + (y - prev_y) * smooth
            if abs(ix - prev_x) > eps or abs(iy - prev_y) > eps:
                pg.moveTo(ix, iy)
                prev_x, prev_y = ix, iy
        cv2.imshow("Hand Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    stream.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
