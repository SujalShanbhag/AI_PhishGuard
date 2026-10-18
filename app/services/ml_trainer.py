import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix
)
from sklearn.ensemble import (
    RandomForestClassifier, HistGradientBoostingClassifier,
    ExtraTreesClassifier, AdaBoostClassifier, BaggingClassifier,
    VotingClassifier, StackingClassifier
)
from sklearn.linear_model import (
    LogisticRegression, SGDClassifier, RidgeClassifier, PassiveAggressiveClassifier
)
from sklearn.svm import LinearSVC
from sklearn.neural_network import MLPClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB, BernoulliNB
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis

from app.config import settings

class MLTrainerService:
    def __init__(self):
        self.models_dir = Path(settings.MODELS_DIR) / "ml_algorithms"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.datasets_dir = Path(settings.DATASETS_DIR)
        self.supported_algorithms = {
            "random_forest": {
                "name": "Random Forest Classifier",
                "family": "Ensemble (Bagging)",
                "description": "Constructs an ensemble of 100 decision trees with bootstrap aggregation for robust classification with high resistance to overfitting."
            },
            "extra_trees": {
                "name": "Extra Trees Classifier",
                "family": "Ensemble (Extremely Randomized)",
                "description": "Ensemble of extremely randomized trees optimizing decision cut-points randomly for minimum variance and fast training."
            },
            "gradient_boosting": {
                "name": "Histogram Gradient Boosting",
                "family": "Ensemble (Boosting)",
                "description": "Iteratively fits regression trees to negative gradients of the loss function, offering state-of-the-art tabular accuracy."
            },
            "adaboost": {
                "name": "AdaBoost Adaptive Boosting",
                "family": "Ensemble (Adaptive Boosting)",
                "description": "Sequentially re-weights misclassified training instances with an ensemble of boosted decision stumps."
            },
            "bagging": {
                "name": "Bagging Classifier",
                "family": "Ensemble (Bootstrap Aggregation)",
                "description": "Bootstrap aggregating ensemble averaging multiple base estimators to drastically suppress predictive variance."
            },
            "voting_ensemble": {
                "name": "Soft-Voting Ensemble Classifier",
                "family": "Meta-Ensemble",
                "description": "Consensus voting meta-estimator combining probabilistic outputs of Random Forest, Gradient Boosting, and Logistic Regression."
            },
            "stacking_classifier": {
                "name": "Stacking Meta-Classifier",
                "family": "Meta-Ensemble",
                "description": "Two-tier stacked generalization training a logistic regression meta-model on predictions of heterogeneous base classifiers."
            },
            "logistic_regression": {
                "name": "Logistic Regression (L2)",
                "family": "Linear Model",
                "description": "Calibrated probabilistic linear classifier with L2 ridge regularization for high interpretability and speed."
            },
            "ridge": {
                "name": "Ridge Classifier (L2 Regularized)",
                "family": "Linear Model",
                "description": "Tikhonov L2 regularized linear model converting binary classification into ridge regression targets."
            },
            "sgd": {
                "name": "Stochastic Gradient Descent (SGD)",
                "family": "Linear Model",
                "description": "Scalable linear classifier fitted with stochastic gradient descent with log-loss optimization."
            },
            "passive_aggressive": {
                "name": "Passive-Aggressive Classifier",
                "family": "Online Linear Model",
                "description": "Margin-based online classification algorithm aggressively updating weights on margin violations."
            },
            "svm": {
                "name": "Support Vector Machine (Linear SVM)",
                "family": "Kernel / Margin-Based",
                "description": "Maximizes geometric classification margin in feature space with hinge loss minimization."
            },
            "linear_discriminant": {
                "name": "Linear Discriminant Analysis (LDA)",
                "family": "Discriminant Analysis",
                "description": "Finds a linear combination of features that separates classes under Gaussian distribution assumptions."
            },
            "quadratic_discriminant": {
                "name": "Quadratic Discriminant Analysis (QDA)",
                "family": "Discriminant Analysis",
                "description": "Generates quadratic decision boundaries allowing individual class-specific covariance matrices."
            },
            "mlp_neural_network": {
                "name": "Multi-Layer Perceptron (MLP Neural Net)",
                "family": "Neural Network",
                "description": "Feedforward artificial neural network with multiple hidden layers (64x32), ReLU activations, and Adam optimizer."
            },
            "decision_tree": {
                "name": "Decision Tree Classifier (CART)",
                "family": "Tree-Based",
                "description": "Non-parametric supervised model partitioning feature space using optimal Gini impurity splits."
            },
            "knn": {
                "name": "K-Nearest Neighbors (KNN, k=5)",
                "family": "Instance-Based (Metric)",
                "description": "Distance-weighted metric classification comparing query vectors to k-nearest training exemplars."
            },
            "naive_bayes": {
                "name": "Gaussian Naive Bayes",
                "family": "Bayesian Probabilistic",
                "description": "Fast probabilistic model applying Bayes theorem with continuous Gaussian feature assumptions."
            },
            "bernoulli_nb": {
                "name": "Bernoulli Naive Bayes",
                "family": "Bayesian Probabilistic",
                "description": "Probabilistic model optimized for discrete binary and boolean indicator feature sets."
            }
        }

    def _normalize_key(self, key: str) -> str:
        k = key.lower().strip()
        if k in ["phishing", "real_world_phishing"]:
            return "real_world_phishing"
        elif k in ["fraud", "real_world_fraud"]:
            return "real_world_fraud"
        elif k in ["document_forgery", "real_world_document_forgery", "forgery"]:
            return "real_world_document_forgery"
        elif k in ["synthetic_10k", "synthetic_kyc_cyber", "kyc"]:
            return "synthetic_kyc_cyber"
        return k

    def _get_algorithm_instance(self, algo_key: str):
        if algo_key == "random_forest":
            return RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=1)
        elif algo_key == "extra_trees":
            return ExtraTreesClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=1)
        elif algo_key == "gradient_boosting":
            return HistGradientBoostingClassifier(max_iter=100, max_depth=8, random_state=42)
        elif algo_key == "adaboost":
            return AdaBoostClassifier(n_estimators=100, random_state=42)
        elif algo_key == "bagging":
            return BaggingClassifier(n_estimators=50, random_state=42, n_jobs=1)
        elif algo_key == "voting_ensemble":
            return VotingClassifier(
                estimators=[
                    ('rf', RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=1)),
                    ('gb', HistGradientBoostingClassifier(max_iter=50, random_state=42)),
                    ('lr', LogisticRegression(max_iter=500, random_state=42))
                ],
                voting='soft'
            )
        elif algo_key == "stacking_classifier":
            return StackingClassifier(
                estimators=[
                    ('rf', RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=1)),
                    ('dt', DecisionTreeClassifier(max_depth=6, random_state=42))
                ],
                final_estimator=LogisticRegression(max_iter=500, random_state=42)
            )
        elif algo_key == "logistic_regression":
            return LogisticRegression(max_iter=1000, C=1.0, random_state=42)
        elif algo_key == "ridge":
            return RidgeClassifier(random_state=42)
        elif algo_key == "sgd":
            return SGDClassifier(loss="log_loss", max_iter=1000, random_state=42)
        elif algo_key == "passive_aggressive":
            return PassiveAggressiveClassifier(max_iter=1000, random_state=42)
        elif algo_key == "svm":
            return LinearSVC(max_iter=2000, random_state=42, dual=False)
        elif algo_key == "linear_discriminant":
            return LinearDiscriminantAnalysis()
        elif algo_key == "quadratic_discriminant":
            return QuadraticDiscriminantAnalysis()
        elif algo_key == "mlp_neural_network":
            return MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=300, random_state=42)
        elif algo_key == "decision_tree":
            return DecisionTreeClassifier(max_depth=10, random_state=42)
        elif algo_key == "knn":
            return KNeighborsClassifier(n_neighbors=5, n_jobs=1)
        elif algo_key == "naive_bayes":
            return GaussianNB()
        elif algo_key == "bernoulli_nb":
            return BernoulliNB()
        else:
            raise ValueError(f"Unsupported algorithm: {algo_key}")

    def prepare_dataset(self, dataset_key: str) -> Tuple[pd.DataFrame, pd.Series, List[str], str]:
        """
        Loads and prepares feature matrix X and target vector y across all 4 datasets.
        """
        norm_key = self._normalize_key(dataset_key)

        if norm_key == "real_world_phishing":
            csv_path = self.datasets_dir / "real_world_phishing_dataset.csv"
            df = pd.read_csv(csv_path)
            feature_cols = [
                'url_length', 'count_dots', 'count_hyphens', 'count_slashes',
                'has_at_symbol', 'uses_https_ssl', 'ip_address_in_host',
                'character_entropy', 'subdomain_count', 'phishing_keywords_found'
            ]
            X = df[feature_cols].copy().fillna(0)
            y = (df['classification_label'] != 'LEGITIMATE').astype(int)
            target_name = "Is Phishing Threat"

        elif norm_key == "real_world_fraud":
            csv_path = self.datasets_dir / "real_world_fraud_dataset.csv"
            df = pd.read_csv(csv_path)
            channel_map = {"UPI": 1, "NEFT": 2, "IMPS": 3, "NET_BANKING": 4, "CARD": 5}
            df['channel_encoded'] = df['channel'].map(channel_map).fillna(0)
            df['is_high_risk_country'] = df['ip_origin_country'].apply(lambda c: 0 if c == "IN" else 1)
            feature_cols = [
                'channel_encoded', 'amount_inr', 'old_balance_orig',
                'new_balance_orig', 'is_high_risk_country'
            ]
            X = df[feature_cols].copy().fillna(0)
            y = df['is_fraud_flag'].astype(int)
            target_name = "Is Financial Fraud"

        elif norm_key == "real_world_document_forgery":
            csv_path = self.datasets_dir / "real_world_document_forgery_benchmarks.csv"
            df = pd.read_csv(csv_path)
            feature_cols = [
                'mean_ela_error', 'max_differential_error', 'error_level_variance',
                'surface_laplacian_sharpness', 'tampering_confidence'
            ]
            X = df[feature_cols].copy().fillna(0)
            y = (df['ground_truth_label'] == 'TAMPERED').astype(int)
            target_name = "Is Document Forged / Tampered"

        elif norm_key == "synthetic_kyc_cyber":
            csv_path = self.datasets_dir / "synthetic_kyc_cyber_10000rows.csv"
            if not csv_path.exists():
                csv_path = self.datasets_dir / "synthetic_kyc_cyber_large.csv"
            df = pd.read_csv(csv_path)
            df['mfa_num'] = df['mfa_enabled'].apply(lambda v: 1 if v in [True, "True", "TRUE", 1] else 0)
            df['gender_num'] = df['gender'].apply(lambda g: 1 if g == "Female" else (0 if g == "Male" else 2))
            feature_cols = [
                'age', 'annual_income_inr', 'credit_score',
                'cyber_risk_score', 'mfa_num', 'gender_num'
            ]
            X = df[feature_cols].copy().fillna(0)
            y = df['fraud_flag'].apply(lambda f: 0 if f == "CLEAN" else 1).astype(int)
            target_name = "KYC Threat / Risk Flag"
        else:
            raise ValueError(f"Unknown dataset key: {dataset_key}")

        return X, y, feature_cols, target_name

    def train_models(
        self,
        dataset_key: str,
        algorithms: Optional[List[str]] = None,
        test_size: float = 0.20
    ) -> Dict[str, Any]:
        """
        Trains selected ML algorithms on the Train partition, rigorously tests them
        on the unseen Test partition, and returns side-by-side Train vs Test metrics.
        """
        norm_key = self._normalize_key(dataset_key)
        if not algorithms:
            algorithms = list(self.supported_algorithms.keys())

        X, y, feature_cols, target_name = self.prepare_dataset(norm_key)

        # Explicit Train/Test Partitioning
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        scaler = StandardScaler()
        X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=feature_cols)
        X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=feature_cols)

        results = []
        best_model_name = None
        best_f1 = -1.0

        for algo_key in algorithms:
            if algo_key not in self.supported_algorithms:
                continue

            algo_meta = self.supported_algorithms[algo_key]
            clf = self._get_algorithm_instance(algo_key)

            t0 = time.time()
            clf.fit(X_train_scaled, y_train)
            train_duration_ms = round((time.time() - t0) * 1000, 2)

            # 1. Performance on Train Set
            y_train_pred = clf.predict(X_train_scaled)
            train_acc = float(accuracy_score(y_train, y_train_pred))

            # 2. Performance on Unseen Test Set
            y_test_pred = clf.predict(X_test_scaled)
            test_acc = float(accuracy_score(y_test, y_test_pred))
            test_prec = float(precision_score(y_test, y_test_pred, zero_division=0))
            test_rec = float(recall_score(y_test, y_test_pred, zero_division=0))
            test_f1 = float(f1_score(y_test, y_test_pred, zero_division=0))

            # ROC-AUC on Test Set
            y_test_score = None
            if hasattr(clf, "predict_proba"):
                y_test_score = clf.predict_proba(X_test_scaled)[:, 1]
            elif hasattr(clf, "decision_function"):
                y_test_score = clf.decision_function(X_test_scaled)

            test_roc_auc = None
            if y_test_score is not None:
                try:
                    test_roc_auc = float(roc_auc_score(y_test, y_test_score))
                except Exception:
                    test_roc_auc = None

            cm = confusion_matrix(y_test, y_test_pred).tolist()

            # Feature importances
            importances = {}
            if hasattr(clf, "feature_importances_"):
                imp = np.asarray(clf.feature_importances_).flatten()
                for col, val in zip(feature_cols, imp):
                    importances[col] = round(float(val), 4)
            elif hasattr(clf, "coef_"):
                raw_coef = np.asarray(clf.coef_)
                if raw_coef.ndim == 1:
                    imp = np.abs(raw_coef)
                elif raw_coef.ndim >= 2:
                    imp = np.abs(raw_coef[0])
                else:
                    imp = []
                for col, val in zip(feature_cols, imp):
                    importances[col] = round(float(val), 4)

            # Probabilities for test samples
            if y_test_score is not None:
                try:
                    if np.any(y_test_score < 0) or np.any(y_test_score > 1):
                        y_test_prob = 1.0 / (1.0 + np.exp(-np.clip(y_test_score, -20, 20)))
                    else:
                        y_test_prob = y_test_score
                except Exception:
                    y_test_prob = None
            else:
                y_test_prob = None

            # Sample test evaluations (first 6 samples from test set)
            test_samples = []
            for idx in range(min(6, len(X_test))):
                sample_features = X_test.iloc[idx].to_dict()
                true_label = int(y_test.iloc[idx])
                pred_label = int(y_test_pred[idx])
                confidence = float(y_test_prob[idx]) if y_test_prob is not None else (0.95 if pred_label == 1 else 0.05)
                confidence = max(0.01, min(0.99, confidence))
                test_samples.append({
                    "sample_id": f"TEST-{idx + 1:03d}",
                    "features": sample_features,
                    "ground_truth": "THREAT / TAMPERED" if true_label == 1 else "LEGITIMATE / CLEAN",
                    "predicted": "THREAT / TAMPERED" if pred_label == 1 else "LEGITIMATE / CLEAN",
                    "confidence_score": round(confidence * 100, 1),
                    "is_correct": bool(true_label == pred_label)
                })

            # Save model bundle
            model_filename = f"{norm_key}_{algo_key}.joblib"
            model_path = self.models_dir / model_filename
            bundle = {
                "algorithm_key": algo_key,
                "algorithm_name": algo_meta["name"],
                "dataset_key": norm_key,
                "feature_cols": feature_cols,
                "scaler": scaler,
                "model": clf,
                "metrics": {
                    "train_accuracy": round(train_acc, 4),
                    "test_accuracy": round(test_acc, 4),
                    "precision": round(test_prec, 4),
                    "recall": round(test_rec, 4),
                    "f1_score": round(test_f1, 4),
                    "roc_auc": round(test_roc_auc, 4) if test_roc_auc else None,
                    "train_time_ms": train_duration_ms
                },
                "test_samples": test_samples,
                "confusion_matrix": cm
            }
            joblib.dump(bundle, str(model_path))

            if test_f1 > best_f1:
                best_f1 = test_f1
                best_model_name = algo_meta["name"]

            results.append({
                "algorithm_key": algo_key,
                "name": algo_meta["name"],
                "family": algo_meta["family"],
                "train_accuracy": round(train_acc * 100, 2),
                "accuracy": round(test_acc * 100, 2),
                "precision": round(test_prec * 100, 2),
                "recall": round(test_rec * 100, 2),
                "f1_score": round(test_f1 * 100, 2),
                "roc_auc": round(test_roc_auc * 100, 2) if test_roc_auc else None,
                "train_time_ms": train_duration_ms,
                "confusion_matrix": cm,
                "test_samples": test_samples,
                "feature_importances": importances,
                "model_file": model_filename
            })

        results.sort(key=lambda r: r["f1_score"], reverse=True)

        return {
            "status": "SUCCESS",
            "dataset_key": norm_key,
            "target_variable": target_name,
            "total_samples": len(X),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "train_ratio": round((1 - test_size) * 100, 1),
            "test_ratio": round(test_size * 100, 1),
            "features_used": feature_cols,
            "best_model": best_model_name,
            "models_evaluated": len(results),
            "leaderboard": results
        }

    def evaluate_test_set(
        self,
        dataset_key: str,
        algorithm_key: str = "random_forest",
        test_size: float = 0.20
    ) -> Dict[str, Any]:
        """
        Executes an on-demand test evaluation on the unseen test partition.
        """
        norm_key = self._normalize_key(dataset_key)
        model_filename = f"{norm_key}_{algorithm_key}.joblib"
        model_path = self.models_dir / model_filename

        if not model_path.exists():
            self.train_models(norm_key, [algorithm_key], test_size=test_size)

        bundle = joblib.load(str(model_path))
        X, y, feature_cols, target_name = self.prepare_dataset(norm_key)

        _, X_test, _, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        scaler = bundle["scaler"]
        clf = bundle["model"]
        X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=feature_cols)

        y_pred = clf.predict(X_test_scaled)
        test_acc = float(accuracy_score(y_test, y_pred))
        test_prec = float(precision_score(y_test, y_pred, zero_division=0))
        test_rec = float(recall_score(y_test, y_pred, zero_division=0))
        test_f1 = float(f1_score(y_test, y_pred, zero_division=0))

        y_score = None
        if hasattr(clf, "predict_proba"):
            y_score = clf.predict_proba(X_test_scaled)[:, 1]
        elif hasattr(clf, "decision_function"):
            y_score = clf.decision_function(X_test_scaled)

        test_roc_auc = None
        if y_score is not None:
            try:
                test_roc_auc = float(roc_auc_score(y_test, y_score))
            except Exception:
                test_roc_auc = None

        cm = confusion_matrix(y_test, y_pred).tolist()

        y_prob = None
        if y_score is not None:
            try:
                if np.any(y_score < 0) or np.any(y_score > 1):
                    y_prob = 1.0 / (1.0 + np.exp(-np.clip(y_score, -20, 20)))
                else:
                    y_prob = y_score
            except Exception:
                y_prob = None

        test_samples = []
        for idx in range(min(10, len(X_test))):
            sample_features = X_test.iloc[idx].to_dict()
            true_label = int(y_test.iloc[idx])
            pred_label = int(y_pred[idx])
            prob_val = float(y_prob[idx]) if y_prob is not None else (0.92 if pred_label == 1 else 0.08)
            prob_val = max(0.01, min(0.99, prob_val))
            test_samples.append({
                "sample_id": f"TEST-SET-{idx + 1:03d}",
                "features": sample_features,
                "ground_truth": "THREAT / TAMPERED" if true_label == 1 else "LEGITIMATE / CLEAN",
                "predicted": "THREAT / TAMPERED" if pred_label == 1 else "LEGITIMATE / CLEAN",
                "confidence_score": round(prob_val * 100, 1),
                "is_correct": bool(true_label == pred_label)
            })

        return {
            "status": "SUCCESS",
            "dataset_key": norm_key,
            "algorithm": bundle["algorithm_name"],
            "test_samples_count": len(X_test),
            "test_accuracy": round(test_acc * 100, 2),
            "precision": round(test_prec * 100, 2),
            "recall": round(test_rec * 100, 2),
            "f1_score": round(test_f1 * 100, 2),
            "roc_auc": round(test_roc_auc * 100, 2) if test_roc_auc else None,
            "metrics": {
                "test_accuracy": round(test_acc * 100, 2),
                "precision": round(test_prec * 100, 2),
                "recall": round(test_rec * 100, 2),
                "f1_score": round(test_f1 * 100, 2),
                "roc_auc": round(test_roc_auc * 100, 2) if test_roc_auc else None
            },
            "confusion_matrix": cm,
            "test_samples": test_samples
        }

    def predict(
        self,
        dataset_key: str,
        algorithm_key: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes live inference using a previously trained model pipeline.
        """
        norm_key = self._normalize_key(dataset_key)
        model_filename = f"{norm_key}_{algorithm_key}.joblib"
        model_path = self.models_dir / model_filename

        if not model_path.exists():
            self.train_models(norm_key, [algorithm_key])

        bundle = joblib.load(str(model_path))
        feature_cols = bundle["feature_cols"]
        scaler = bundle["scaler"]
        clf = bundle["model"]

        vector = []
        for col in feature_cols:
            val = input_data.get(col, 0)
            try:
                vector.append(float(val))
            except (ValueError, TypeError):
                vector.append(0.0)

        vec_df = pd.DataFrame([vector], columns=feature_cols)
        vec_scaled = scaler.transform(vec_df)

        pred_class = int(clf.predict(vec_scaled)[0])
        prob = None
        if hasattr(clf, "predict_proba"):
            try:
                prob = float(clf.predict_proba(vec_scaled)[0][1])
            except Exception:
                prob = None
        elif hasattr(clf, "decision_function"):
            try:
                raw_df = float(clf.decision_function(vec_scaled)[0])
                prob = float(1.0 / (1.0 + np.exp(-np.clip(raw_df, -20, 20))))
            except Exception:
                prob = None
        if prob is None:
            prob = 0.92 if pred_class == 1 else 0.08

        label = "MALICIOUS / SUSPICIOUS" if pred_class == 1 else "LEGITIMATE / CLEAN"
        risk_tier = "CRITICAL" if (prob and prob > 0.85) else ("HIGH" if pred_class == 1 else "LOW")

        return {
            "prediction": pred_class,
            "verdict": label,
            "probability": round(prob * 100, 2) if prob is not None else None,
            "risk_tier": risk_tier,
            "algorithm": bundle["algorithm_name"],
            "dataset": norm_key,
            "features_evaluated": dict(zip(feature_cols, vector))
        }

    def get_leaderboard(self, dataset_key: str = "real_world_phishing") -> Dict[str, Any]:
        """
        Retrieves or initializes the current trained models leaderboard.
        """
        norm_key = self._normalize_key(dataset_key)
        saved_files = list(self.models_dir.glob(f"{norm_key}_*.joblib"))
        if not saved_files:
            return self.train_models(norm_key)

        leaderboard = []
        for f in saved_files:
            try:
                bundle = joblib.load(str(f))
                m = bundle.get("metrics", {})
                algo_key = bundle.get("algorithm_key", "")
                algo_meta = self.supported_algorithms.get(algo_key, {"name": algo_key, "family": "ML"})
                leaderboard.append({
                    "algorithm_key": algo_key,
                    "name": bundle.get("algorithm_name", algo_meta["name"]),
                    "family": algo_meta.get("family", "ML"),
                    "train_accuracy": round(m.get("train_accuracy", 0.0) * 100, 2),
                    "accuracy": round(m.get("test_accuracy", m.get("accuracy", 0.0)) * 100, 2),
                    "precision": round(m.get("precision", 0.0) * 100, 2),
                    "recall": round(m.get("recall", 0.0) * 100, 2),
                    "f1_score": round(m.get("f1_score", 0.0) * 100, 2),
                    "roc_auc": round(m.get("roc_auc", 0.0) * 100, 2) if m.get("roc_auc") else None,
                    "train_time_ms": m.get("train_time_ms", 0.0),
                    "test_samples": bundle.get("test_samples", []),
                    "model_file": f.name
                })
            except Exception:
                continue

        leaderboard.sort(key=lambda r: r["f1_score"], reverse=True)
        return {
            "status": "SUCCESS",
            "dataset_key": norm_key,
            "models_evaluated": len(leaderboard),
            "leaderboard": leaderboard
        }


ml_trainer_service = MLTrainerService()
