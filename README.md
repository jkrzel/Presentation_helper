# Hand Gesture Control Using OpenCV, MediaPipe and PyAutoGUI
This Python program enables real-time hand tracking and gesture recognition using a webcam. It combines MediaPipe for hand landmark detection, OpenCV for video processing, and PyAutoGUI to control the computer's mouse cursor based on hand movements.

Project Description:
The application captures video from the webcam, processes each frame to detect hand position and gestures using MediaPipe's powerful hand tracking solution, and translates those gestures into mouse movements or actions using PyAutoGUI. This allows you to control your computer with hand gestures — without touching a mouse or keyboard.

Technologies Used:
    - Python – main programming language
    - OpenCV – for video capture and image processing
    - MediaPipe – for real-time hand landmark detection
    - PyAutoGUI – to control the mouse cursor and perform GUI actions based on gestures

Key Features:
    - Real-time hand tracking from webcam input
    - Detection of hand landmarks and finger positions
    - Mouse cursor movement based on hand coordinates
    - Potential for gesture-based clicks or additional controls

This project demonstrates how to integrate multiple libraries to build an intuitive computer interaction system using only your camera and hand gestures.

Installation
Make sure you have Python 3.7 or newer installed.

Install the required libraries:
    pip install opencv-python mediapipe pyautogui
⚠ On some systems, you may also need:
    pip install numpy
