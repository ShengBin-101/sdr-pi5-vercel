from flask import Flask, jsonify, request, render_template, Response
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from io import BytesIO

app = Flask(__name__)

# Global storage for predictions
predictions = {"class": "Waiting...", "spectrogram": None}

# ---------------------------------
# Route: Main page (serves index.html)
# ---------------------------------
@app.route("/")
def index():
    # Ensure index.html is in a 'templates/' folder so Flask can find it
    return render_template("index.html")

# ---------------------------------
# Route: Return JSON of current class
# ---------------------------------
@app.route("/data", methods=["GET"])
def data():
    return jsonify({"class": predictions["class"]})

# ---------------------------------
# Route: Return spectrogram as PNG
# ---------------------------------
@app.route("/spectrogram", methods=["GET"])
def spectrogram_image():
    if predictions["spectrogram"] is None:
        return "No spectrogram available yet.", 404

    # Convert stored list back to numpy array
    spec_array = np.array(predictions["spectrogram"])

    fig = Figure(figsize=(8, 4))
    ax = fig.add_subplot(111)
    im = ax.imshow(spec_array, aspect='auto', cmap='viridis')
    ax.set_title("Live Spectrogram")
    ax.set_xlabel("Time")
    ax.set_ylabel("Frequency")
    fig.colorbar(im, ax=ax, label="Power (dB)")

    # Write PNG to memory
    buf = BytesIO()
    FigureCanvas(fig).print_png(buf)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='image/png')

# ---------------------------------
# Route: Receive new prediction/spectrogram from Pi
# ---------------------------------
@app.route("/updatePrediction", methods=["POST"])
def update_prediction():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400

    # Update global predictions
    predictions["class"] = data.get("class", "Unknown")
    predictions["spectrogram"] = data.get("spectrogram", None)  # 2D list from Pi

    return jsonify({"status": "success"}), 200

# ---------------------------------
# Main
# ---------------------------------
if __name__ == "__main__":
    app.run(debug=True)