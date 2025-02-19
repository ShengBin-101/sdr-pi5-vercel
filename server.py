from flask import Flask, jsonify, render_template, Response, request
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvas
from io import BytesIO
import time

app = Flask(__name__)

# -----------------------------
# 1) Keep old predictions storage
# -----------------------------
predictions = {"class": "Waiting...", "spectrogram": None}

# -----------------------------
# 2) Class to store Pi feed data
# -----------------------------
class PiFeedStorage:
    def __init__(self):
        self.latest_frame = None  # Will hold raw JPEG bytes
        self.drone_count = 0

    def set_frame(self, frame_bytes):
        self.latest_frame = frame_bytes

    def set_drone_count(self, count):
        self.drone_count = count

    def get_drone_count(self):
        return self.drone_count

    def generate_frames(self):
        """
        Yields the stored frame as an MJPEG stream for /video_feed.
        """
        while True:
            if self.latest_frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       self.latest_frame + b'\r\n')
            else:
                time.sleep(0.1)

# A single global instance to store the RPi's data
pi_storage = PiFeedStorage()

# -----------------------------
# 3) All your old endpoints
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data", methods=["GET"])
def data():
    return jsonify({"class": predictions["class"]})

@app.route("/spectrogram", methods=["GET"])
def spectrogram_image():
    if predictions["spectrogram"] is None:
        return "No spectrogram available yet.", 404

    spec_array = np.array(predictions["spectrogram"])
    fig = Figure(figsize=(8, 4))
    ax = fig.add_subplot(111)
    im = ax.imshow(spec_array, aspect='auto', cmap='viridis')
    ax.set_title("Live Spectrogram")
    ax.set_xlabel("Time")
    ax.set_ylabel("Frequency")
    fig.colorbar(im, ax=ax, label="Power (dB)")

    buf = BytesIO()
    FigureCanvas(fig).print_png(buf)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='image/png')

@app.route("/updatePrediction", methods=["POST"])
def update_prediction():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400
    predictions["class"] = data.get("class", "Unknown")
    predictions["spectrogram"] = data.get("spectrogram", None)
    return jsonify({"status": "success"}), 200

# -----------------------------
# 4) UNCHANGED /video_feed
# -----------------------------
@app.route("/video_feed")
def video_feed():
    # Serve the frames from pi_storage
    return Response(pi_storage.generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# -----------------------------
# 5) UNCHANGED /drone_count
# -----------------------------
@app.route("/drone_count")
def drone_count():
    return jsonify({"count": pi_storage.get_drone_count()})

# -----------------------------
# 6) NEW ENDPOINT: /update_feed
# -----------------------------
@app.route("/update_feed", methods=["POST"])
def update_feed():
    """
    The Pi posts the latest frame + drone_count here.
    We'll store them in pi_storage.
    """
    file = request.files.get('frame', None)
    drone_count_str = request.form.get('drone_count', '0')

    # If we got a frame, store it
    if file:
        frame_bytes = file.read()  # raw JPEG bytes
        pi_storage.set_frame(frame_bytes)

    # Convert the drone count to int
    try:
        drone_count_int = int(drone_count_str)
    except ValueError:
        drone_count_int = 0
    pi_storage.set_drone_count(drone_count_int)

    return jsonify({"status": "success"}), 200

# CORS (if needed)
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

if __name__ == "__main__":
    # We do NOT run any YOLO code here! 
    # The Pi pushes frames via /update_feed.
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
