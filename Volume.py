import cv2
import mediapipe as mp
import numpy as np
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# Initialize Mediapipe for hand detection
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

# Initialize pycaw for volume control
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))

# Get the current volume range
vol_range = volume.GetVolumeRange()
min_vol = vol_range[0]
max_vol = vol_range[1]

# Start capturing video from webcam
cap = cv2.VideoCapture(1)

def calculate_distance(point1, point2):
    """Calculate the Euclidean distance between two points."""
    return np.linalg.norm(np.array(point1) - np.array(point2))

while True:
    success, img = cap.read()
    if not success:
        break

    # Convert the image to RGB for Mediapipe
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Draw the hand landmarks
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Get landmark positions for thumb tip and index finger tip
            thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]

            # Convert to pixel coordinates
            h, w, c = img.shape
            thumb_tip_coords = (int(thumb_tip.x * w), int(thumb_tip.y * h))
            index_tip_coords = (int(index_tip.x * w), int(index_tip.y * h))

            # Draw circles on thumb and index finger tips
            cv2.circle(img, thumb_tip_coords, 10, (0, 255, 0), cv2.FILLED)
            cv2.circle(img, index_tip_coords, 10, (0, 255, 0), cv2.FILLED)

            # Calculate distance between thumb and index finger tips
            distance = calculate_distance(thumb_tip_coords, index_tip_coords)

            # Map the distance to a volume range
            vol = np.interp(distance, [20, 200], [min_vol, max_vol])
            volume.SetMasterVolumeLevel(vol, None)

            # Display the volume on the screen
            cv2.putText(img, f'Volume: {int(np.interp(distance, [20, 200], [0, 100]))}%', (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

    # Show the image with landmarks and volume level
    cv2.imshow("Hand Tracking", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
