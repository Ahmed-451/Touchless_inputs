import cv2
import mediapipe as mp
import numpy as np
import pyttsx3
import time

# Initialize Mediapipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

# Initialize text-to-speech engine
engine = pyttsx3.init()

# Set the voice to female
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)  # Select female voice, may vary based on system

# Define the virtual keyboard layout including space bar, read button, delete button, and clear button with padding
keys = [
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
    ['Z', 'X', 'C', 'V', 'B', 'N', 'M'],
    ['SPACE', 'READ', 'DELETE', 'CLEAR']  # Space bar, read button, delete button, and clear button
]

# Define the keyboard dimensions and positioning
key_size = 80
key_margin = 15
start_x = (1280 - (10 * key_size + 9 * key_margin)) // 2  # Centering the keyboard horizontally
start_y = (720 - (4 * key_size + 3 * key_margin)) // 2  # Centering the keyboard vertically
space_key_size = 200  # Size of the space bar
read_key_size = 150  # Size of the read button
delete_key_size = 200  # Size of the delete button
clear_key_size = 150  # Size of the clear button
padding = 20  # Padding between keys

# Define the new video window dimensions
video_width = 1280
video_height = 720

# Define pinch threshold distance
PINCH_THRESHOLD = 30

# Initialize typed text and delete button status
typed_text = ""
delete_pressed = False
clear_pressed = False
last_delete_time = time.time()
DELETE_INTERVAL = 0.1  # Time interval for deleting characters

# Track the last key pressed and debounce mechanism
last_key_pressed = None
last_press_time = 0
press_delay = 0.5  # 500ms delay between valid presses

# Flag to check if greeting has been spoken
greeting_spoken = False


def draw_curved_rect(img, x, y, w, h, radius, color, alpha=0.6, thickness=-1):
    """Draws a rectangle with rounded corners and transparency"""

    overlay = img.copy()  # Create an overlay that will be blended
    # Draw the filled rounded rectangle on the overlay
    cv2.rectangle(overlay, (x + radius, y), (x + w - radius, y + h), color, thickness)
    cv2.rectangle(overlay, (x, y + radius), (x + w, y + h - radius), color, thickness)
    cv2.ellipse(overlay, (x + radius, y + radius), (radius, radius), 180, 0, 90, color, thickness)
    cv2.ellipse(overlay, (x + w - radius, y + radius), (radius, radius), 270, 0, 90, color, thickness)
    cv2.ellipse(overlay, (x + radius, y + h - radius), (radius, radius), 90, 0, 90, color, thickness)
    cv2.ellipse(overlay, (x + w - radius, y + h - radius), (radius, radius), 0, 0, 90, color, thickness)

    # Blend the overlay with the original image to add transparency
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)  # 'img' is updated with the blended result

def draw_keys(img, key_highlight=None):
    for i, row in enumerate(keys):
        for j, key in enumerate(row):
            x = start_x + j * (key_size + key_margin)
            y = start_y + i * (key_size + key_margin)

            if key == 'SPACE':
                x += (key_size - space_key_size) // 2  # Center space key
                w, h = space_key_size, key_size
            elif key == 'READ':
                x += space_key_size + padding  # Adjust x for space key size and padding
                w, h = read_key_size, key_size
            elif key == 'DELETE':
                x += space_key_size + padding + read_key_size + padding  # Adjust x for previous keys and padding
                w, h = delete_key_size, key_size
            elif key == 'CLEAR':
                x += space_key_size + padding + read_key_size + padding + delete_key_size + padding  # Adjust x for previous keys and padding
                w, h = clear_key_size, key_size
            else:
                w, h = key_size, key_size

            # Change the key background color to black and highlight the pressed key with a green glow effect
            color = (0, 255, 0) if key == key_highlight else (30, 30, 30)

            # Add curved edges to the keys
            draw_curved_rect(img, x, y, w, h, radius=20, color=color)

            # Change the key letter color to white
            cv2.putText(img, key, (x + w // 4, y + h // 2 + 10), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)


def detect_keypress(finger_x, finger_y):
    for i, row in enumerate(keys):
        for j, key in enumerate(row):
            x = start_x + j * (key_size + key_margin)
            y = start_y + i * (key_size + key_margin)

            if key == 'SPACE':
                x += (key_size - space_key_size) // 2  # Adjust x for space key size
                w, h = space_key_size, key_size
            elif key == 'READ':
                x += space_key_size + padding  # Adjust x for space key size and padding
                w, h = read_key_size, key_size
            elif key == 'DELETE':
                x += space_key_size + padding + read_key_size + padding  # Adjust x for previous keys and padding
                w, h = delete_key_size, key_size
            elif key == 'CLEAR':
                x += space_key_size + padding + read_key_size + padding + delete_key_size + padding  # Adjust x for previous keys and padding
                w, h = clear_key_size, key_size
            else:
                w, h = key_size, key_size

            if x < finger_x < x + w and y < finger_y < y + h:
                return key
    return None


def calculate_distance(p1, p2):
    return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def draw_text_field(img, text):
    # Calculate the width of the text
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)[0]
    # Calculate field width, adjusting for padding
    field_w = text_size[0] + 20
    # Define text field height and position
    field_h = 80
    field_x = (video_width - field_w) // 2  # Center the text field horizontally
    field_y = video_height - 100  # Fixed position from the bottom

    # Draw text field background
    cv2.rectangle(img, (field_x, field_y), (field_x + field_w, field_y + field_h), (0, 0, 0), cv2.FILLED)
    # Draw text field border
    cv2.rectangle(img, (field_x, field_y), (field_x + field_w, field_y + field_h), (255, 255, 255), 2)
    # Put text in the text field
    cv2.putText(img, text, (field_x + 10, field_y + field_h // 2 + 10), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)


# OpenCV setup
cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, video_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, video_height)

# Display the window
cv2.namedWindow("AI Virtual Keyboard", cv2.WINDOW_AUTOSIZE)

# Main loop
while True:
    success, img = cap.read()
    if not success:
        break

    img = cv2.flip(img, 1)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    result = hands.process(img_rgb)

    key_pressed = None
    current_time = time.time()

    if not greeting_spoken:
        # Text-to-speech greeting after the window is opened
        engine.say("Hello, I'm Jarvis. Opening the AI Virtual Keyboard")
        engine.runAndWait()
        greeting_spoken = True  # Set the flag to True after speaking

    if result.multi_hand_landmarks:
        for hand_lms in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

            # Get hand landmark positions
            lm_list = []
            for id, lm in enumerate(hand_lms.landmark):
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append([id, cx, cy])

            if lm_list:
                # Get the coordinates for the index finger (ID 8) and thumb (ID 4)
                x_index, y_index = lm_list[8][1], lm_list[8][2]
                x_thumb, y_thumb = lm_list[4][1], lm_list[4][2]

                # Calculate distance between the index finger and thumb
                distance = calculate_distance((x_index, y_index), (x_thumb, y_thumb))

                if distance < PINCH_THRESHOLD and (current_time - last_press_time) > press_delay:
                    key_pressed = detect_keypress(x_index, y_index)
                    if key_pressed:
                        # Print and add the detected key to the text field
                        print(f"Key Pressed: {key_pressed}")

                        # Handle key presses
                        if key_pressed == 'SPACE':
                            typed_text += ' '
                        elif key_pressed == 'READ':
                            engine.say(typed_text)
                            engine.runAndWait()
                        elif key_pressed == 'DELETE':
                            if typed_text:  # Ensure there is text to delete
                                typed_text = typed_text[:-1]
                                last_delete_time = time.time()
                        elif key_pressed == 'CLEAR':
                            typed_text = ''  # Clear the text field
                        else:
                            # Register the key press and update the last press time
                            typed_text += key_pressed
                            last_press_time = current_time

    # Draw the virtual keyboard and highlight the pressed key
    draw_keys(img, key_highlight=key_pressed)
    # Draw the text field with the current typed text
    draw_text_field(img, typed_text)

    # Display the result
    cv2.imshow("AI Virtual Keyboard", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
