import cv2
import smtplib
from email.mime.text import MIMEText
from flask import Flask, Response
from plyer import notification
import threading

# Flask app for streaming
app = Flask(__name__)

# Email alert function
def send_alert_email():
    sender_email = "EmailToUse@gmail.com"
    receiver_email = "youremail@gmail.com"
    password = "sender_email_password"

    message = MIMEText("Motion detected!")
    message['Subject'] = "CCTV Alert"
    message['From'] = sender_email
    message['To'] = receiver_email

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(message)
        print("Alert email sent.")
    except Exception as e:
        print(f"Error sending email: {e}")

# Desktop notification function
def send_desktop_notification():
    notification.notify(
        title="Motion Detected!",
        message="Motion detected by CCTV system.",
        timeout=5
    )

# Video frame generator for streaming
def generate_frames():
    global cap
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Motion detection function
def detect_motion():
    global cap
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    ret, frame1 = cap.read()
    if not ret:
        print("Error: Could not read initial frame.")
        return
    frame1_gray = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    frame1_gray = cv2.GaussianBlur(frame1_gray, (21, 21), 0)

    while True:
        ret, frame2 = cap.read()
        if not ret:
            break

        frame2_gray = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        frame2_gray = cv2.GaussianBlur(frame2_gray, (21, 21), 0)

        frame_diff = cv2.absdiff(frame1_gray, frame2_gray)
        thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        motion_detected = False

        for contour in contours:
            if cv2.contourArea(contour) < 1000:
                continue
            motion_detected = True
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(frame2, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cv2.imshow('Motion Detection', frame2)

        # Send alerts if motion is detected
        if motion_detected:
            send_alert_email()
            send_desktop_notification()

        frame1_gray = frame2_gray

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# Run Flask app in a separate thread
def start_streaming():
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

lock = threading.Lock()

def generate_frames():
	global cap
	while True:
		with lock:
			success, frame = cap.read()
			if not success:
				break
			_, buffer = cv2.imencode('.jpg', frame)
			frame = buffer.tobytes()
			yield (b' --frame\r\n'
				b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
# Main function to combine everything
if __name__ == "__main__":
    # Start the streaming thread
    streaming_thread = threading.Thread(target=start_streaming, daemon=True)
    streaming_thread.start()

    # Start motion detection
    detect_motion()
