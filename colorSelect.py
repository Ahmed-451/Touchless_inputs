import cv2
import mediapipe as mp
import numpy as np

# Initialize Mediapipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_draw = mp.solutions.drawing_utils

# Define color palette
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 165, 0), (128, 0, 128)]
color_names = ['Red', 'Green', 'Blue', 'Yellow', 'Orange', 'Purple']
selected_color = None  # No default color selected

# Shape colors
circle_color = (255, 255, 255)  # Default circle color
triangle_color = (255, 255, 255)  # Default triangle color

# Define the video window dimensions and the virtual shapes
video_width = 1280
video_height = 720
circle_center = (400, 360)  # Center of the circle
circle_radius = 100  # Radius of the circle
triangle_center = (800, 360)  # Center of the triangle
triangle_size = 100  # Size of the triangle
PINCH_THRESHOLD = 30

# OpenCV setup
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open the camera.")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, video_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, video_height)

# Display the window
cv2.namedWindow("Color Shapes", cv2.WINDOW_AUTOSIZE)


def draw_color_palette(img):
    """Draws a circular color palette on the screen."""
    center_x = 200
    center_y = 100
    radius = 100
    num_colors = len(colors)

    for i in range(num_colors):
        angle = 2 * np.pi * i / num_colors
        color_x = int(center_x + radius * np.cos(angle))
        color_y = int(center_y + radius * np.sin(angle))
        cv2.circle(img, (color_x, color_y), 30, colors[i], -1)  # Draw color circle
        cv2.putText(img, color_names[i], (color_x - 20, color_y + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)


def select_color(finger_x, finger_y):
    """Selects a color from the circular palette based on finger position."""
    center_x = 200
    center_y = 100
    radius = 100
    for i in range(len(colors)):
        angle = 2 * np.pi * i / len(colors)
        color_x = int(center_x + radius * np.cos(angle))
        color_y = int(center_y + radius * np.sin(angle))
        if (finger_x - color_x) ** 2 + (finger_y - color_y) ** 2 < 30 ** 2:  # Check if finger is within color circle
            return colors[i]
    return None


def draw_shapes(img):
    """Draws the two shapes on the screen."""
    # Draw circle
    cv2.circle(img, circle_center, circle_radius, (255, 255, 255), 2)  # Circle outline
    cv2.circle(img, circle_center, circle_radius, circle_color, -1)  # Fill with current color

    # Draw triangle
    triangle_points = np.array([
        (triangle_center[0], triangle_center[1] - triangle_size),  # Top
        (triangle_center[0] - triangle_size, triangle_center[1] + triangle_size),  # Bottom left
        (triangle_center[0] + triangle_size, triangle_center[1] + triangle_size)  # Bottom right
    ])
    cv2.polylines(img, [triangle_points], isClosed=True, color=(255, 255, 255), thickness=2)  # Triangle outline
    cv2.fillPoly(img, [triangle_points], triangle_color)  # Fill triangle with current color


def is_point_in_circle(point, center, radius):
    """Checks if a point is inside a circle."""
    return np.linalg.norm(np.array(point) - np.array(center)) < radius


def is_point_in_triangle(point, triangle):
    """Checks if a point is inside a triangle."""
    A = triangle[0]
    B = triangle[1]
    C = triangle[2]
    area_ABC = 0.5 * (-B[1] * C[0] + A[1] * (-B[0] + C[0]) + A[0] * (B[1] - C[1]) + B[0] * C[1])
    s = 1 / (2 * area_ABC) * (A[1] * C[0] - A[0] * C[1] + (C[1] - A[1]) * point[0] + (A[0] - C[0]) * point[1])
    t = 1 / (2 * area_ABC) * (A[0] * B[1] - A[1] * B[0] + (A[1] - B[1]) * point[0] + (B[0] - A[0]) * point[1])
    return s >= 0 and t >= 0 and (s + t) <= 1


# Main loop
while True:
    success, img = cap.read()
    if not success:
        print("Error: Could not read frame from the camera.")
        break

    img = cv2.flip(img, 1)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    result = hands.process(img_rgb)

    color_dragging = False  # Reset dragging state
    shape_selected = False  # Reset shape selected state

    if result.multi_hand_landmarks:
        for hand_lms in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

            # Get hand landmark positions
            lm_list = []
            for id, lm in enumerate(hand_lms.landmark):
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append((cx, cy))

            # Check for pinching gesture
            if lm_list:
                index_finger = lm_list[8]  # Index finger tip
                thumb_tip = lm_list[4]  # Thumb tip

                distance = np.sqrt((index_finger[0] - thumb_tip[0]) ** 2 + (index_finger[1] - thumb_tip[1]) ** 2)

                if distance < PINCH_THRESHOLD:
                    # Check if over circle
                    if is_point_in_circle(index_finger, circle_center, circle_radius):
                        shape_selected = "circle"
                    # Check if over triangle
                    triangle_points = np.array([
                        (triangle_center[0], triangle_center[1] - triangle_size),  # Top
                        (triangle_center[0] - triangle_size, triangle_center[1] + triangle_size),  # Bottom left
                        (triangle_center[0] + triangle_size, triangle_center[1] + triangle_size)  # Bottom right
                    ])
                    if is_point_in_triangle(index_finger, triangle_points):
                        shape_selected = "triangle"

                    # Detect color selection
                    finger_x, finger_y = index_finger
                    selected_color_candidate = select_color(finger_x, finger_y)

                    if selected_color_candidate:
                        selected_color = selected_color_candidate  # Set the selected color

                # If dragging over a shape and releasing
                if shape_selected and selected_color:
                    # Change the color of the selected shape
                    if shape_selected == "circle":
                        circle_color = selected_color  # Apply color to circle
                    elif shape_selected == "triangle":
                        triangle_color = selected_color  # Apply color to triangle

                    # Reset selected color after applying it
                    selected_color = None

    # Draw the color palette and the shapes
    draw_color_palette(img)
    draw_shapes(img)

    # Display the result
    cv2.imshow("Color Shapes", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
