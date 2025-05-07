import cv2
import mediapipe as mp
import pyautogui as pg
import time

pg.FAILSAFE = True

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils


def get_index_finger_coordinates(image):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = hands.process(image_rgb)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            index_finger_tip = hand_landmarks.landmark[8]
            screen_size = pg.size()
            x = int(index_finger_tip.x * screen_size[0])
            y = int(index_finger_tip.y * screen_size[1])
            return (x, y)

    return None


def main():
    cap = cv2.VideoCapture(0)
    prev_time = time.time()

    prev_x, prev_y = None, None
    smoothening = 0.8
    epsilon = 10  # minimalny ruch w pikselach, by uznać to za zmianę pozycji

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        coordinates = get_index_finger_coordinates(frame)

        curr_time = time.time()
        fps = 1 / (curr_time - prev_time)
        prev_time = curr_time
        print(f"FPS: {fps:.2f}")

        if coordinates:
            x, y = coordinates

            if prev_x is None or prev_y is None:
                prev_x, prev_y = x, y

            # interpolacja
            interp_x = prev_x + (x - prev_x) * smoothening
            interp_y = prev_y + (y - prev_y) * smoothening

            dx = abs(interp_x - prev_x)
            dy = abs(interp_y - prev_y)

            # jeśli ruch jest większy niż epsilon – ruszamy kursor
            if dx >= epsilon or dy >= epsilon:
                pg.moveTo(interp_x, interp_y, duration=0.05)
                prev_x, prev_y = interp_x, interp_y

            # debug info
            #print(f"Kursor: ({int(interp_x)}, {int(interp_y)})")

        cv2.imshow("Hand Tracking", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
