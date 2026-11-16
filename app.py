import math
from pathlib import Path

from flask import Flask, jsonify, render_template, request
import joblib
import numpy as np
from werkzeug.exceptions import BadRequest, UnsupportedMediaType


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model" / "model.pkl"
FEATURES = [
    "MedInc", "HouseAge", "AveRooms", "AveBedrms",
    "Population", "AveOccup", "Latitude", "Longitude",
]


def validate_features(features):
    if not isinstance(features, list) or len(features) != len(FEATURES):
        raise ValueError(f"Expected 8 features in this order: {', '.join(FEATURES)}")
    for name, value in zip(FEATURES, features):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a finite number, not text or a boolean.")
        try:
            valid = math.isfinite(value) and abs(value) <= float(np.finfo(np.float32).max)
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError(f"{name} must be a finite number within the model's numeric range.")
    return features


def create_app(model_path=MODEL_PATH):
    application = Flask(__name__)
    application.config["MAX_CONTENT_LENGTH"] = 16 * 1024
    if not Path(model_path).is_file():
        raise RuntimeError("Model not found. Run: python train_model.py")
    model = joblib.load(model_path)

    @application.get("/health")
    def health():
        return jsonify(ok=True, features=FEATURES)

    @application.errorhandler(413)
    def request_too_large(error):
        return jsonify(error="Request is too large. Send only the 8 feature values."), 413

    @application.post("/predict")
    def predict():
        try:
            payload = request.get_json()
        except (BadRequest, UnsupportedMediaType):
            return jsonify(error="Send valid JSON with Content-Type: application/json."), 400
        if not isinstance(payload, dict):
            return jsonify(error="Expected a JSON object containing a features array."), 400
        try:
            features = validate_features(payload.get("features"))
        except ValueError as error:
            return jsonify(error=str(error)), 400
        prediction = float(model.predict(np.asarray([features], dtype=float))[0])
        return jsonify(prediction=prediction)

    @application.route("/", methods=["GET", "POST"])
    def main():
        if request.method == "GET":
            return render_template("main.html", values={})
        try:
            features = validate_features([float(request.form.get(name, "")) for name in FEATURES])
        except (TypeError, ValueError):
            return render_template(
                "main.html", values=request.form,
                error="Enter a finite numeric value for every one of the 8 fields.",
            ), 400
        prediction = float(model.predict(np.asarray([features], dtype=float))[0])
        return render_template("main.html", values=request.form, prediction=prediction)

    return application


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
