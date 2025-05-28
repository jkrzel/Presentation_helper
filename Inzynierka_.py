import cv2
import mediapipe as mp
import pyautogui as pg
import time
from threading import Thread
import math

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


def dist(a, b, w, h):
    return math.hypot((a.x - b.x) * w, (a.y - b.y) * h)


def is_open_palm(lm, w, h):
    palm_size = dist(lm.landmark[0], lm.landmark[9], w, h)
    tips = [8, 12, 16, 20]
    joints = [5, 9, 13, 17]
    for tip, joint in zip(tips, joints):
        if dist(lm.landmark[tip], lm.landmark[joint], w, h) < palm_size * 0.6:
            return False
    return True


def detect_gesture(multi_landmarks, multi_handedness, w, h):
    if len(multi_landmarks) == 1:
        label = multi_handedness[0].classification[0].label
        lm = multi_landmarks[0]
        if label == 'Left' and is_open_palm(lm, w, h):
            return 'CIRCLE'
    if len(multi_landmarks) == 2:
        lm1, lm2 = multi_landmarks
        if dist(lm1.landmark[4], lm1.landmark[8], w, h) < w * 0.05 and \
           dist(lm2.landmark[4], lm2.landmark[8], w, h) < w * 0.05:
            return 'Resize'
    if len(multi_landmarks) >= 1:
        lm = multi_landmarks[0]
        palm = dist(lm.landmark[0], lm.landmark[9], w, h)
        t_i = dist(lm.landmark[4], lm.landmark[8], w, h)
        t_m = dist(lm.landmark[4], lm.landmark[12], w, h)
        f_i = dist(lm.landmark[8], lm.landmark[5], w, h)
        f_m = dist(lm.landmark[12], lm.landmark[9], w, h)
        pinch_thresh = palm * 0.5
        fold_thresh = palm * 0.7
        if t_i < pinch_thresh and f_m > fold_thresh:
            return 'Thumb-Index'
        if t_m < pinch_thresh and f_i > fold_thresh:
            return 'Thumb-Middle'
    return 'No Gesture'


def main():
    pg.FAILSAFE = True
    pg.PAUSE = 0

    stream = WebcamStream().start()
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        model_complexity=0,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    mp_drawing = mp.solutions.drawing_utils

    prev_x = prev_y = 0
    smooth = 0.8
    eps = 10

    while True:
        frame = stream.read()
        if frame is None:
            continue

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        gesture = 'No Gesture'
        if results.multi_hand_landmarks:
            gesture = detect_gesture(
                results.multi_hand_landmarks,
                results.multi_handedness,
                w, h
            )
            for lm in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame, lm, mp_hands.HAND_CONNECTIONS
                )

            idx = results.multi_hand_landmarks[0].landmark[8]
            sw, sh = pg.size()
            x = int(idx.x * sw)
            y = int(idx.y * sh)
            ix = prev_x + (x - prev_x) * smooth
            iy = prev_y + (y - prev_y) * smooth
            if abs(ix - prev_x) > eps or abs(iy - prev_y) > eps:
                pg.moveTo(ix, iy)
                prev_x, prev_y = ix, iy

        cv2.putText(
            frame,
            f"Gesture: {gesture}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )
        cv2.imshow("Hand Tracking with Gesture", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    stream.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
