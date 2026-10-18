import os
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

# Set loky CPU count to avoid Windows warning
os.environ["LOKY_MAX_CPU_COUNT"] = "4"

from app.security.authentication import get_current_user
from app.models.database_models import User
from app.services.ml_trainer import ml_trainer_service

router = APIRouter(prefix="/api/ml", tags=["Machine Learning Training Studio"])

class TrainRequest(BaseModel):
    dataset_key: str = Field(..., description="Target dataset: real_world_phishing, real_world_fraud, real_world_document_forgery, or synthetic_kyc_cyber")
    algorithms: Optional[List[str]] = Field(default=None, description="List of algorithm keys to train")
    test_size: float = Field(default=0.20, ge=0.1, le=0.5, description="Test split ratio")

class TestRequest(BaseModel):
    dataset_key: str = Field(..., description="Target dataset name")
    algorithm_key: str = Field(default="random_forest", description="Trained model algorithm")
    test_size: float = Field(default=0.20, ge=0.1, le=0.5, description="Test split ratio")

class PredictRequest(BaseModel):
    dataset_key: str = Field(..., description="Target dataset name")
    algorithm_key: str = Field(default="random_forest", description="Trained model algorithm")
    input_data: Dict[str, Any] = Field(..., description="Feature key-value dictionary")

@router.get("/algorithms")
def get_supported_algorithms():
    """Returns catalog of supported machine learning algorithms."""
    return {
        "status": "SUCCESS",
        "algorithms": ml_trainer_service.supported_algorithms
    }

@router.get("/datasets")
def get_available_datasets():
    """Returns available training datasets with schemas."""
    return {
        "status": "SUCCESS",
        "datasets": [
            {
                "key": "real_world_phishing",
                "name": "Real-World Phishing URL & Cyber Threat Dataset",
                "samples": 1500,
                "target": "is_phishing (0=Legitimate, 1=Phishing/Malware)",
                "features": ["url_length", "count_dots", "count_hyphens", "count_slashes", "has_at_symbol", "uses_https_ssl", "ip_address_in_host", "character_entropy", "subdomain_count", "phishing_keywords_found"]
            },
            {
                "key": "real_world_fraud",
                "name": "Real-World Financial Transaction Fraud Benchmark",
                "samples": 1000,
                "target": "is_fraud_flag (0=Legitimate, 1=Fraudulent)",
                "features": ["channel_encoded", "amount_inr", "old_balance_orig", "new_balance_orig", "is_high_risk_country"]
            },
            {
                "key": "real_world_document_forgery",
                "name": "Real-World Document Forgery & Tampering Benchmark",
                "samples": 40,
                "target": "is_tampered (0=Genuine, 1=Tampered/Forged)",
                "features": ["mean_ela_error", "max_differential_error", "error_level_variance", "surface_laplacian_sharpness", "tampering_confidence"]
            },
            {
                "key": "synthetic_kyc_cyber",
                "name": "Large-Scale Synthetic KYC & Cyber Risk Dataset",
                "samples": 10000,
                "target": "fraud_flag (0=Clean, 1=Threat/Review Required)",
                "features": ["age", "annual_income_inr", "credit_score", "cyber_risk_score", "mfa_num", "gender_num"]
            }
        ]
    }

@router.post("/train")
def train_models_endpoint(
    req: TrainRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Trains selected ML algorithms on the chosen dataset.
    Returns real evaluation metrics, confusion matrices, and leaderboard comparisons.
    """
    try:
        results = ml_trainer_service.train_models(
            dataset_key=req.dataset_key,
            algorithms=req.algorithms,
            test_size=req.test_size
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Training failed: {str(e)}")

@router.post("/test")
def test_model_endpoint(
    req: TestRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Evaluates a trained ML model on the unseen test dataset partition.
    Returns unseen test metrics, confusion matrix, and individual test samples inspection.
    """
    try:
        results = ml_trainer_service.evaluate_test_set(
            dataset_key=req.dataset_key,
            algorithm_key=req.algorithm_key,
            test_size=req.test_size
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Test evaluation failed: {str(e)}")

@router.get("/leaderboard")
def get_leaderboard_endpoint(
    dataset_key: str = Query("real_world_phishing", description="Dataset key")
):
    """Retrieves current model benchmark leaderboard."""
    try:
        return ml_trainer_service.get_leaderboard(dataset_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/predict")
def predict_endpoint(
    req: PredictRequest,
    current_user: User = Depends(get_current_user)
):
    """Executes live prediction on input features using a trained ML model."""
    try:
        return ml_trainer_service.predict(
            dataset_key=req.dataset_key,
            algorithm_key=req.algorithm_key,
            input_data=req.input_data
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prediction error: {str(e)}")
