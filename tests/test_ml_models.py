import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.ml_trainer import ml_trainer_service

client = TestClient(app)

EXPECTED_ALGORITHMS = [
    "random_forest", "extra_trees", "gradient_boosting", "adaboost",
    "bagging", "voting_ensemble", "stacking_classifier",
    "logistic_regression", "ridge", "sgd", "passive_aggressive",
    "svm", "linear_discriminant", "quadratic_discriminant",
    "mlp_neural_network", "decision_tree", "knn", "naive_bayes", "bernoulli_nb"
]

def test_ml_algorithms_catalog():
    res = client.get("/api/ml/algorithms")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert len(data["algorithms"]) == len(EXPECTED_ALGORITHMS)
    for algo in EXPECTED_ALGORITHMS:
        assert algo in data["algorithms"]
        assert "name" in data["algorithms"][algo]
        assert "family" in data["algorithms"][algo]

def test_ml_datasets_catalog():
    res = client.get("/api/ml/datasets")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    dataset_keys = [d["key"] for d in data["datasets"]]
    assert "real_world_phishing" in dataset_keys
    assert "real_world_fraud" in dataset_keys
    assert "real_world_document_forgery" in dataset_keys
    assert "synthetic_kyc_cyber" in dataset_keys

def test_ml_service_train_and_benchmark():
    # Test service directly with 3 algorithms
    res = ml_trainer_service.train_models(
        dataset_key="real_world_phishing",
        algorithms=["random_forest", "logistic_regression", "gradient_boosting"],
        test_size=0.20
    )
    assert res["status"] == "SUCCESS"
    assert res["models_evaluated"] == 3
    assert len(res["leaderboard"]) == 3
    for m in res["leaderboard"]:
        assert m["train_accuracy"] >= 80.0
        assert m["accuracy"] >= 80.0
        assert m["f1_score"] >= 80.0
        assert m["train_time_ms"] >= 0.0
        assert len(m["confusion_matrix"]) == 2
        assert len(m["test_samples"]) > 0

def test_ml_service_evaluate_test_set():
    res = ml_trainer_service.evaluate_test_set(
        dataset_key="real_world_phishing",
        algorithm_key="random_forest",
        test_size=0.20
    )
    assert res["status"] == "SUCCESS"
    assert res["test_accuracy"] >= 80.0
    assert res["test_samples_count"] > 0
    assert len(res["test_samples"]) > 0
    sample = res["test_samples"][0]
    assert "sample_id" in sample
    assert "ground_truth" in sample
    assert "predicted" in sample
    assert "is_correct" in sample

def test_ml_service_live_prediction():
    input_sample = {
        "url_length": 95,
        "count_dots": 4,
        "count_hyphens": 2,
        "count_slashes": 3,
        "has_at_symbol": 1,
        "uses_https_ssl": 0,
        "ip_address_in_host": 0,
        "character_entropy": 5.1,
        "subdomain_count": 3,
        "phishing_keywords_found": 3
    }
    pred = ml_trainer_service.predict("real_world_phishing", "random_forest", input_sample)
    assert "prediction" in pred
    assert "verdict" in pred
    assert "probability" in pred
    assert pred["prediction"] == 1  # Should be flagged as malicious
    assert "MALICIOUS" in pred["verdict"]

def test_ml_test_endpoint_authenticated():
    email = "ml_test_user@phishguard.ai"
    pwd = "SecureMLPassword123!"
    client.post("/api/auth/register", json={"email": email, "password": pwd})
    login_res = client.post("/api/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    res = client.post(
        "/api/ml/test",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "dataset_key": "real_world_phishing",
            "algorithm_key": "random_forest",
            "test_size": 0.20
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "test_accuracy" in data
    assert "test_samples" in data

def test_ml_leaderboard_retrieval():
    res = client.get("/api/ml/leaderboard?dataset_key=real_world_phishing")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert len(data["leaderboard"]) > 0

def test_ml_train_all_19_algorithms():
    # Train all 19 algorithms in one batch to ensure no scikit-learn compatibility issues
    res = ml_trainer_service.train_models(
        dataset_key="real_world_phishing",
        algorithms=EXPECTED_ALGORITHMS,
        test_size=0.20
    )
    assert res["status"] == "SUCCESS"
    assert res["models_evaluated"] == len(EXPECTED_ALGORITHMS)
    assert len(res["leaderboard"]) == len(EXPECTED_ALGORITHMS)
    trained_algos = {m["algorithm_key"] for m in res["leaderboard"]}
    assert trained_algos == set(EXPECTED_ALGORITHMS)

