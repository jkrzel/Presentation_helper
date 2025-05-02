import cv2
import mediapipe as mp
import pyautogui as pg

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
            #cv2.circle(image, (x, y), 10, (0, 255, 0), -1)
            #cv2.putText(image, f"Palec(x,y): ({x}, {y})", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            return (x, y)

    return None

def main():
    cap = cv2.VideoCapture(0)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.flip(frame, 1)
        coordinates = get_index_finger_coordinates(frame)


        if coordinates:
            print(f"Kordy: {coordinates}")
            pg.moveTo(coordinates[0], coordinates[1], duration=0)
        
        cv2.imshow("", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
