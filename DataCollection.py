import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import time
import os
import sys

GESTURE_CLASSES = {
    'NO_HAND': 0,        # No hand detected / Idle state 
    'SCROLL_UP': 1,
    'SCROLL_DOWN': 2,
    'SWIPE_LEFT': 3,
    'SWIPE_RIGHT': 4,
    'PLAY_PAUSE': 5,
    'BACK_NAV': 6,
}
NUM_SAMPLES = 500  # Number of frames to collect per non-idle gesture
CSV_FILE_PATH = os.path.join('Data', 'gesture_data.csv')

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
NUM_FEATURES = 21 * 3 


def get_landmark_header():
    """Generates the CSV header row for the 21 hand landmarks (x, y, z) and the label."""
    header = []
    for i in range(21):
        header.extend([f'x{i}', f'y{i}', f'z{i}'])
    header.append('class_id')
    return header

def extract_keypoints(results):
    """
    Extracts the normalized 21 hand landmarks (x, y, z) into a flattened 1D array (63 values).
    Returns a NumPy array of 63 zeros if no hand is detected.
    """
    keypoints = np.zeros(NUM_FEATURES) # Initialize with zeros (for NO_HAND/NO_DETECTION)
    if results.multi_hand_landmarks:
        hand = results.multi_hand_landmarks[0]
        keypoints = np.array([[lm.x, lm.y, lm.z] for lm in hand.landmark]).flatten()
        
        if keypoints.size != NUM_FEATURES:
            print(f"Warning: Extracted {keypoints.size} features instead of {NUM_FEATURES}. Returning zeros.")
            return np.zeros(NUM_FEATURES) 
    
    return keypoints

def collect_data():
    """Opens the webcam and collects data samples for each defined gesture class."""
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam (Camera index 0). Please check camera connection or change index.")
        sys.exit(1)

    if not os.path.exists(os.path.dirname(CSV_FILE_PATH)):
        os.makedirs(os.path.dirname(CSV_FILE_PATH))

    if not os.path.exists(CSV_FILE_PATH):
        print(f"Creating new CSV file: {CSV_FILE_PATH}")
        with open(CSV_FILE_PATH, 'w', newline='') as f:
            f.write(','.join(get_landmark_header()) + '\n')
    
    gesture_labels_to_collect = [g for g in GESTURE_CLASSES.keys() if g != 'NO_HAND']

    with mp_hands.Hands(
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
        max_num_hands=1) as hands:

        for gesture_name in gesture_labels_to_collect:
            class_id = GESTURE_CLASSES[gesture_name]
            samples_collected = 0

            print(f"\n--- Prepare for: {gesture_name} (Class ID: {class_id}) ---")
            for i in range(3, 0, -1):
                ret, frame = cap.read()
                if not ret: break

                frame = cv2.flip(frame, 1) 
                display_text = f"GET READY for: {gesture_name}"
                cv2.putText(frame, display_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, f"Recording starts in: {i}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
                cv2.imshow('Data Collection Feed', frame)
                cv2.waitKey(1000) 

            print(f"Recording {NUM_SAMPLES} samples for {gesture_name}...")
            while samples_collected < NUM_SAMPLES:
                ret, frame = cap.read()
                if not ret: break

                frame = cv2.flip(frame, 1)
                image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(image_rgb)
                
                keypoints = extract_keypoints(results)

                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        mp_drawing.draw_landmarks(
                            frame, hand_landmarks, mp_hands.HAND_CONNECTIONS, 
                            mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2), 
                            mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2)  
                        )
                    
                    row = np.append(keypoints, class_id)
                    
                    with open(CSV_FILE_PATH, 'a', newline='') as f:
                        f.write(','.join(map(str, row)) + '\n')
                    
                    samples_collected += 1
                
                status_text = f"Recording: {gesture_name} ({samples_collected}/{NUM_SAMPLES})"
                cv2.putText(frame, status_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
                cv2.imshow('Data Collection Feed', frame)

                if cv2.waitKey(10) & 0xFF == ord('q'):
                    print("Exiting data collection early.")
                    cap.release()
                    cv2.destroyAllWindows()
                    sys.exit(0)
            
            print(f"-> Collected {samples_collected} samples for {gesture_name}")
            time.sleep(1) 

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nPhase 1 Complete. Dataset saved at: {CSV_FILE_PATH}")

if __name__ == '__main__':
    collect_data()
