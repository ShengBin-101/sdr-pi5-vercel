from flask import Flask, jsonify, render_template, Response, request
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvas
from io import BytesIO
import time

app = Flask(__name__)

# Predictions for acoustic part
predictions = {"class": "Waiting...", "spectrogram": None}

class PiFeedStorage:
    def __init__(self):
        self.latest_frame = None  # raw JPEG
        self.drone_count = 0

    def set_frame(self, frame_bytes):
        self.latest_frame = frame_bytes

    def set_drone_count(self, count):
        self.drone_count = count

    def get_drone_count(self):
        return self.drone_count

# One global instance
pi_storage = PiFeedStorage()

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
    import base64
    try:
        img_bytes = base64.b64decode(predictions["spectrogram"])
    except Exception as e:
        return "Error decoding spectrogram.", 500
    return Response(img_bytes, mimetype='image/png')

@app.route("/updatePrediction", methods=["POST"])
def update_prediction():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400
    predictions["class"] = data.get("class", "Unknown")
    predictions["spectrogram"] = data.get("spectrogram", None)
    return jsonify({"status": "success"}), 200

@app.route("/drone_count")
def drone_count():
    return jsonify({"count": pi_storage.get_drone_count()})

# ---------------------------------------------------------------------
# SINGLE Image at /video_feed (no streaming)
# Each HTTP request returns the current JPEG, then closes.
# ---------------------------------------------------------------------
@app.route("/video_feed")
def video_feed():
    if pi_storage.latest_frame is None:
        return "No frame available", 404
    # Return the single latest frame
    return Response(pi_storage.latest_frame, mimetype='image/jpeg')

@app.route("/update_feed", methods=["POST"])
def update_feed():
    file = request.files.get('frame', None)
    drone_count_str = request.form.get('drone_count', '0')

    if file:
        frame_bytes = file.read()
        pi_storage.set_frame(frame_bytes)

    try:
        drone_count_int = int(drone_count_str)
    except ValueError:
        drone_count_int = 0
    pi_storage.set_drone_count(drone_count_int)

    return jsonify({"status": "success"}), 200

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

if __name__ == "__main__":
    # We do NOT run any YOLO code here! 
    # The Pi pushes frames via /update_feed.
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
