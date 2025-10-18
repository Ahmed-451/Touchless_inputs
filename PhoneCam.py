import cv2

# Capture video from the webcam (in this case, the iPhone via EpocCam or iVCam)
cap = cv2.VideoCapture(1)  # '0' will use the default webcam, which should be the iPhone if it's streaming

while True:
    success, frame = cap.read()
    if not success:
        print("Failed to capture image")
        break

    # Display the captured frame
    cv2.imshow('iPhone Camera Feed', frame)

    # Press 'q' to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the capture when done
cap.release()
cv2.destroyAllWindows()
