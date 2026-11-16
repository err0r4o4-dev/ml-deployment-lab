import json
from pathlib import Path

import joblib
from sklearn.datasets import fetch_california_housing
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import train_test_split


BASE_DIR = Path(__file__).resolve().parent


def train(output_dir=BASE_DIR / "model", data_home=BASE_DIR / "data"):
    dataset = fetch_california_housing(data_home=str(data_home), as_frame=False)
    train_features, test_features, train_targets, test_targets = train_test_split(
        dataset.data, dataset.target, test_size=0.2, random_state=42
    )
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(train_features, train_targets)
    predictions = model.predict(test_features)
    metrics = {
        "dataset": "California Housing",
        "train_rows": len(train_targets),
        "test_rows": len(test_targets),
        "r2": float(r2_score(test_targets, predictions)),
        "rmse": float(root_mean_squared_error(test_targets, predictions)),
        "mae": float(mean_absolute_error(test_targets, predictions)),
        "target_unit": "USD 100,000",
    }
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / "model.pkl", compress=3)
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    return metrics


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
    print("Model saved to model/model.pkl")
