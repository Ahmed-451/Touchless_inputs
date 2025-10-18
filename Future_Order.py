# Full modified code with voice command support and food images on the menu buttons

import cv2
import mediapipe as mp
import numpy as np
import pyttsx3
import time
from fpdf import FPDF
import os
import webbrowser
from datetime import datetime
import speech_recognition as sr
import threading

# Initialize Mp
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_draw = mp.solutions.drawing_utils

# Initialize tts
engine = pyttsx3.init()
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)  # Female voice

# Prices for each item
prices = {
    "Chicken Burger": 150,
    "Veg Burger": 120,
    "Fries": 80,
    "Coke": 60
}

# Menu layout
keys = [
    ['Chicken Burger', 'Veg Burger', 'Fries', 'Coke'],
    ['Delete', 'Place Order', 'Print Receipt']
]

# Dimensions
key_size = 250
small_key_size = 150
key_margin = 30
video_width = 1280
video_height = 720

start_x = (1280 - (4 * key_size + 3 * key_margin)) // 2
start_y = (720 - (key_size + small_key_size + key_margin)) // 2

PINCH_THRESHOLD = 30
typed_text = ""
ordered_items = []

last_key_pressed = None
last_press_time = 0
press_delay = 0.5
greeting_spoken = False

# Load food images
food_images = {
    "Chicken Burger": cv2.imread("images/chicken_burger.png"),
    "Veg Burger": cv2.imread("images/veg_burger.png"),
    "Fries": cv2.imread("images/fries.png"),
    "Coke": cv2.imread("images/coke.png")
}

def draw_curved_rect(img, x, y, w, h, radius, color, thickness=-1):
    cv2.rectangle(img, (x + radius, y), (x + w - radius, y + h), color, thickness)
    cv2.rectangle(img, (x, y + radius), (x + w, y + h - radius), color, thickness)
    cv2.ellipse(img, (x + radius, y + radius), (radius, radius), 180, 0, 90, color, thickness)
    cv2.ellipse(img, (x + w - radius, y + radius), (radius, radius), 270, 0, 90, color, thickness)
    cv2.ellipse(img, (x + radius, y + h - radius), (radius, radius), 90, 0, 90, color, thickness)
    cv2.ellipse(img, (x + w - radius, y + h - radius), (radius, radius), 0, 0, 90, color, thickness)

def draw_keys(img, key_highlight=None):
    overlay = img.copy()
    for i, key in enumerate(keys[0]):
        x = start_x + i * (key_size + key_margin)
        y = start_y
        w, h = key_size, key_size
        color = (0, 255, 0) if key == key_highlight else (30, 30, 30)
        draw_curved_rect(overlay, x, y, w, h, radius=20, color=color)

        # Draw food image
        if key in food_images and food_images[key] is not None:
            icon = cv2.resize(food_images[key], (80, 80))
            overlay[y + 10:y + 90, x + (w - 80) // 2:x + (w + 80) // 2] = icon

        # Text
        cv2.putText(overlay, key, (x + 10, y + h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    x = start_x
    for key in keys[1]:
        w, h = (300, small_key_size) if key == "Place Order" else (small_key_size, small_key_size)
        y = start_y + key_size + key_margin
        color = (0, 255, 0) if key == key_highlight else (30, 30, 30)
        draw_curved_rect(overlay, x, y, w, h, radius=20, color=color)
        text_scale = 0.9 if key == "Place Order" else 1.0
        cv2.putText(overlay, key, (x + 10, y + h // 2 + 10), cv2.FONT_HERSHEY_SIMPLEX, text_scale, (255, 255, 255), 2)
        x += w + key_margin

    cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)

def detect_keypress(finger_x, finger_y):
    for i, key in enumerate(keys[0]):
        x = start_x + i * (key_size + key_margin)
        y = start_y
        w, h = key_size, key_size
        if x < finger_x < x + w and y < finger_y < y + h:
            return key

    x = start_x
    for key in keys[1]:
        w, h = (300, small_key_size) if key == "Place Order" else (small_key_size, small_key_size)
        y = start_y + key_size + key_margin
        if x < finger_x < x + w and y < finger_y < y + h:
            return key
        x += w + key_margin

    return None

def calculate_distance(p1, p2):
    return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

def draw_text_field(img, text):
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)[0]
    field_w = text_size[0] + 20
    field_h = 80
    field_x = (video_width - field_w) // 2
    field_y = video_height - 100
    cv2.rectangle(img, (field_x, field_y), (field_x + field_w, field_y + field_h), (0, 0, 0), cv2.FILLED)
    cv2.rectangle(img, (field_x, field_y), (field_x + field_w, field_y + field_h), (255, 255, 255), 2)
    cv2.putText(img, text, (field_x + 10, field_y + field_h // 2 + 10), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

# Voice command handler
def voice_command_listener():
    global typed_text, ordered_items
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    command_map = {
        "chicken burger": "Chicken Burger",
        "veg burger": "Veg Burger",
        "fries": "Fries",
        "coke": "Coke",
        "place order": "Place Order",
        "print receipt": "Print Receipt",
        "delete": "Delete"
    }

    while True:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            try:
                audio = recognizer.listen(source, timeout=5)
                command = recognizer.recognize_google(audio).lower()
                for key_phrase in command_map:
                    if key_phrase in command:
                        action = command_map[key_phrase]
                        if action == "Delete":
                            typed_text = typed_text[:-1]
                        elif action == "Place Order":
                            engine.say(f"Your order is: {typed_text}")
                            engine.runAndWait()
                        elif action == "Print Receipt":
                            print_receipt()
                        else:
                            typed_text += action + " "
                            ordered_items.append(action)
                        break
            except:
                continue

# Receipt generator
def print_receipt():
    item_counts = {}
    total_amount = 0
    for item in ordered_items:
        if item in prices:
            item_counts[item] = item_counts.get(item, 0) + 1
            total_amount += prices[item]

    i = 1
    while os.path.exists(f"receipt_{i}.pdf"):
        i += 1
    filename = f"receipt_{i}.pdf"
    now = datetime.now()
    timestamp = now.strftime("%d-%m-%Y, %H:%M:%S")

    pdf = FPDF(format=(80, 297))
    pdf.add_page()
    pdf.set_margins(5, 5, 5)
    pdf.set_font("Courier", 'B', 12)
    pdf.cell(0, 8, "McDonald's", ln=True, align='C')
    pdf.set_font("Courier", '', 10)
    pdf.cell(0, 5, "Virtual Menu Receipt", ln=True, align='C')
    pdf.cell(0, 5, txt=f"Date&Time: {timestamp}", ln=True, align='C')
    pdf.cell(0, 5, "------------------------------", ln=True, align='C')
    for item, count in item_counts.items():
        price = prices[item]
        total = price * count
        line = f"{item:<15}x{count:<2} Rs{total:>5}"
        pdf.cell(0, 6, line, ln=True)
    pdf.cell(0, 5, "------------------------------", ln=True)
    pdf.set_font("Courier", 'B', 11)
    pdf.cell(0, 8, f"TOTAL:           Rs {total_amount}", ln=True)
    pdf.set_font("Courier", '', 9)
    pdf.cell(0, 8, "Thank you! Visit again!", ln=True, align='C')
    pdf.cell(0, 5, "McDonald's Virtual Kiosk", ln=True, align='C')
    pdf.output(filename)
    webbrowser.open(filename)

# Start voice command listener in background
threading.Thread(target=voice_command_listener, daemon=True).start()

cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, video_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, video_height)

cv2.namedWindow("AI Virtual Menu", cv2.WINDOW_AUTOSIZE)

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
        engine.say("Hello, welcome to the McDonald's virtual menu. Please make your selection.")
        engine.runAndWait()
        greeting_spoken = True

    if result.multi_hand_landmarks:
        for hand_lms in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
            lm_list = [(int(lm.x * img.shape[1]), int(lm.y * img.shape[0])) for lm in hand_lms.landmark]

            if lm_list:
                index_finger = lm_list[8]
                thumb_tip = lm_list[4]
                distance = calculate_distance(index_finger, thumb_tip)
                if distance < PINCH_THRESHOLD:
                    finger_x, finger_y = index_finger
                    key_pressed = detect_keypress(finger_x, finger_y)
                    if key_pressed and (current_time - last_press_time > press_delay):
                        if key_pressed == "Delete":
                            typed_text = typed_text[:-1]
                        elif key_pressed == "Place Order":
                            engine.say(f"Your order is: {typed_text}")
                            engine.runAndWait()
                        elif key_pressed == "Print Receipt":
                            print_receipt()
                        else:
                            typed_text += key_pressed + " "
                            ordered_items.append(key_pressed)
                        last_press_time = current_time

    draw_keys(img, key_highlight=key_pressed)
    draw_text_field(img, typed_text)
    cv2.imshow("AI Virtual Menu", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

