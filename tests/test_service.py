import importlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = [8.3, 25.0, 6.0, 1.0, 1200, 3.0, 34.2, -118.3]
FEATURES = [
    "MedInc", "HouseAge", "AveRooms", "AveBedrms",
    "Population", "AveOccup", "Latitude", "Longitude",
]


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("app"), "Flask service is missing")
        self.module = importlib.import_module("app")
        self.client = self.module.app.test_client()

    def test_health_reports_feature_order(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"ok": True, "features": FEATURES})

    def test_real_prediction_is_finite_and_has_expected_scale(self):
        response = self.client.post("/predict", json={"features": SAMPLE})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json), {"prediction"})
        self.assertTrue(math.isfinite(response.json["prediction"]))
        self.assertGreater(response.json["prediction"], 0)
        self.assertLess(response.json["prediction"], 10)

    def test_rejects_wrong_feature_count(self):
        for features in ([], SAMPLE[:-1], SAMPLE + [1]):
            with self.subTest(features=features):
                response = self.client.post("/predict", json={"features": features})
                self.assertEqual(response.status_code, 400)
                self.assertIn("8", response.json["error"])

    def test_rejects_non_object_payload(self):
        for payload in ([], [SAMPLE], "hello", 1, None):
            with self.subTest(payload=payload):
                response = self.client.post(
                    "/predict", data=json.dumps(payload), content_type="application/json"
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json)

    def test_rejects_missing_or_non_list_features(self):
        for payload in ({}, {"features": None}, {"features": "12345678"}, {"features": {}}):
            with self.subTest(payload=payload):
                response = self.client.post("/predict", json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json)

    def test_rejects_invalid_feature_values(self):
        for invalid in (True, False, None, "bad", "8.3", [], {}, 1e300, 10**400):
            with self.subTest(invalid=invalid):
                response = self.client.post("/predict", json={"features": [invalid] + SAMPLE[1:]})
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json)

    def test_rejects_non_finite_values(self):
        for invalid in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(invalid=invalid):
                response = self.client.post("/predict", json={"features": [invalid] + SAMPLE[1:]})
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json)

    def test_rejects_malformed_json_and_wrong_content_type(self):
        for body, content_type in (("{", "application/json"), ("", "application/json"), ("hi", "text/plain")):
            with self.subTest(body=body, content_type=content_type):
                response = self.client.post("/predict", data=body, content_type=content_type)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json)

    def test_rejects_oversized_request(self):
        response = self.client.post(
            "/predict", data='{"extra":"' + "a" * 20000 + '"}', content_type="application/json"
        )
        self.assertEqual(response.status_code, 413)
        self.assertIn("error", response.json)

    def test_predict_requires_post(self):
        self.assertEqual(self.client.get("/predict").status_code, 405)

    def test_home_contains_labeled_inputs_and_units(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        for feature in FEATURES:
            self.assertIn(f'name="{feature}"', html)
            self.assertIn(f'for="{feature}"', html)
        self.assertIn("100,000", html)
        self.assertIn('aria-live="polite"', html)

    def test_form_post_predicts_without_javascript(self):
        response = self.client.post("/", data=dict(zip(FEATURES, SAMPLE)))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Prediction:", response.get_data(as_text=True))

    def test_form_post_reports_bad_input_without_server_error(self):
        response = self.client.post("/", data={"MedInc": "bad"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_data(as_text=True).lower())

    def test_missing_model_explains_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "python train_model.py"):
                self.module.create_app(Path(directory) / "missing.pkl")

    def test_import_and_model_paths_work_outside_project_directory(self):
        command = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "from app import app; "
            "assert app.test_client().get('/health').status_code == 200"
        )
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-c", command, str(ROOT)],
                cwd=directory, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_debug_mode_is_disabled(self):
        self.assertFalse(self.module.app.debug)


class TrainingTests(unittest.TestCase):
    def test_training_produces_loadable_model_and_metrics(self):
        self.assertTrue((ROOT / "train_model.py").exists(), "Training script is missing")
        import joblib
        from train_model import train

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            metrics = train(output_dir=output, data_home=ROOT / "data")
            model = joblib.load(output / "model.pkl")
            self.assertEqual(model.n_features_in_, 8)
            self.assertEqual(model.n_estimators, 100)
            self.assertEqual(model.random_state, 42)
            self.assertTrue(math.isfinite(float(model.predict([SAMPLE])[0])))
            self.assertEqual(metrics["train_rows"], 16512)
            self.assertEqual(metrics["test_rows"], 4128)
            self.assertGreater(metrics["r2"], 0.7)
            self.assertGreater(metrics["rmse"], 0)
            self.assertLess(metrics["rmse"], 1)
            self.assertEqual(json.loads((output / "metrics.json").read_text()), metrics)


if __name__ == "__main__":
    unittest.main()
