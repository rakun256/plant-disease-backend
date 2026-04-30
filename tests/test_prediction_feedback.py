import os
import asyncio

os.environ["DEBUG"] = "false"
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.core.security import create_access_token
from app.db.database import get_db
from app.main import app as fastapi_app
from app.models.base import Base
from app.models.disease import Disease, DiseaseRecommendation
from app.models.prediction import Prediction
from app.models.prediction_feedback import PredictionFeedback
from app.models.user import User
from app.services import prediction_service


SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides.pop(get_current_user, None)
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


def create_user(db_session, email: str) -> User:
    user = User(email=email, hashed_password="hashed-password", full_name="Test User")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_prediction(db_session, user: User) -> Prediction:
    prediction = Prediction(
        user_id=user.id,
        image_name="leaf.jpg",
        predicted_class="rust",
        confidence=0.93,
        inference_time_ms=12.5,
        is_low_confidence=False,
        scores_json='{"healthy": 0.01, "rust": 0.93, "scab": 0.06}',
        model_version="test-model",
    )
    db_session.add(prediction)
    db_session.commit()
    db_session.refresh(prediction)
    return prediction


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.email})
    return {"Authorization": f"Bearer {token}"}


def create_disease(db_session, slug: str = "rust") -> Disease:
    disease = Disease(
        slug=slug,
        name="Cedar Apple Rust",
        description="A fungal disease that may cause yellow to orange leaf spots.",
        symptoms="Yellow-orange spots on apple leaves.",
        causes="A rust fungus favored by wet spring conditions.",
        prevention="Monitor trees, improve airflow, and follow local guidance.",
        severity_level="moderate",
        disclaimer="This information is based on an AI-assisted prediction and general plant disease guidance. It is not a replacement for diagnosis by a qualified agricultural expert.",
    )
    disease.recommendations = [
        DiseaseRecommendation(recommendation="Confirm symptoms on multiple leaves.", order_index=1),
        DiseaseRecommendation(recommendation="Consult a local agricultural expert.", order_index=2),
        DiseaseRecommendation(recommendation="Improve orchard airflow where practical.", order_index=3),
    ]
    db_session.add(disease)
    db_session.commit()
    db_session.refresh(disease)
    return disease


def test_create_prediction_feedback_success(client, db_session):
    user = create_user(db_session, "owner@example.com")
    prediction = create_prediction(db_session, user)

    response = client.post(
        f"/api/v1/predictions/{prediction.id}/feedback",
        headers=auth_headers(user),
        json={
            "is_correct": False,
            "corrected_class": "scab",
            "note": "The model predicted rust, but I think it is scab.",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["prediction_id"] == prediction.id
    assert data["user_id"] == user.id
    assert data["is_correct"] is False
    assert data["corrected_class"] == "scab"
    assert data["note"] == "The model predicted rust, but I think it is scab."
    assert data["created_at"]


def test_create_prediction_feedback_requires_authentication(client, db_session):
    user = create_user(db_session, "owner@example.com")
    prediction = create_prediction(db_session, user)

    response = client.post(
        f"/api/v1/predictions/{prediction.id}/feedback",
        json={"is_correct": True},
    )

    assert response.status_code == 401


def test_create_prediction_feedback_prediction_not_found(client, db_session):
    user = create_user(db_session, "owner@example.com")

    response = client.post(
        "/api/v1/predictions/999/feedback",
        headers=auth_headers(user),
        json={"is_correct": True},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Prediction not found."


def test_create_prediction_feedback_rejects_other_users_prediction(client, db_session):
    owner = create_user(db_session, "owner@example.com")
    other_user = create_user(db_session, "other@example.com")
    prediction = create_prediction(db_session, owner)

    response = client.post(
        f"/api/v1/predictions/{prediction.id}/feedback",
        headers=auth_headers(other_user),
        json={"is_correct": True},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "You can only submit feedback for your own predictions."


def test_create_prediction_feedback_rejects_duplicates(client, db_session):
    user = create_user(db_session, "owner@example.com")
    prediction = create_prediction(db_session, user)
    url = f"/api/v1/predictions/{prediction.id}/feedback"

    first_response = client.post(
        url,
        headers=auth_headers(user),
        json={"is_correct": True},
    )
    duplicate_response = client.post(
        url,
        headers=auth_headers(user),
        json={"is_correct": False, "corrected_class": "scab"},
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == "Feedback already exists for this prediction."


def test_create_prediction_feedback_rejects_invalid_corrected_class(client, db_session):
    user = create_user(db_session, "owner@example.com")
    prediction = create_prediction(db_session, user)

    response = client.post(
        f"/api/v1/predictions/{prediction.id}/feedback",
        headers=auth_headers(user),
        json={"is_correct": False, "corrected_class": "mildew"},
    )

    assert response.status_code == 422


class DummyUploadFile:
    filename = "leaf.jpg"


async def fake_validate_and_open_image(file):
    return object()


def test_prediction_response_includes_latency_and_low_confidence(monkeypatch, db_session):
    user = create_user(db_session, "owner@example.com")

    monkeypatch.setattr(prediction_service, "validate_and_open_image", fake_validate_and_open_image)
    monkeypatch.setattr(prediction_service, "preprocess_image", lambda image: object())
    monkeypatch.setattr(
        prediction_service,
        "predict",
        lambda tensor: ("rust", 0.69, {"healthy": 0.05, "rust": 0.69, "scab": 0.26}),
    )
    monkeypatch.setattr(prediction_service.ml_manager, "model_version", "test-model")

    response = asyncio.run(
        prediction_service.process_prediction(DummyUploadFile(), save_result=False, user=user, db=db_session)
    )

    assert response.inference_time_ms >= 0
    assert response.is_low_confidence is True
    assert response.warning == "The model confidence is low. Please retake the image under better lighting or consult an agricultural expert."


def test_saved_prediction_persists_latency_and_low_confidence(monkeypatch, db_session):
    user = create_user(db_session, "owner@example.com")

    monkeypatch.setattr(prediction_service, "validate_and_open_image", fake_validate_and_open_image)
    monkeypatch.setattr(prediction_service, "preprocess_image", lambda image: object())
    monkeypatch.setattr(
        prediction_service,
        "predict",
        lambda tensor: ("healthy", 0.95, {"healthy": 0.95, "rust": 0.03, "scab": 0.02}),
    )
    monkeypatch.setattr(prediction_service.ml_manager, "model_version", "test-model")

    response = asyncio.run(
        prediction_service.process_prediction(DummyUploadFile(), save_result=True, user=user, db=db_session)
    )
    saved_prediction = db_session.query(Prediction).filter(Prediction.user_id == user.id).one()

    assert response.inference_time_ms >= 0
    assert response.is_low_confidence is False
    assert saved_prediction.inference_time_ms is not None
    assert saved_prediction.inference_time_ms >= 0
    assert saved_prediction.is_low_confidence is False


def test_history_returns_latency_and_low_confidence(client, db_session):
    user = create_user(db_session, "owner@example.com")
    prediction = create_prediction(db_session, user)

    response = client.get("/api/v1/history/", headers=auth_headers(user))

    assert response.status_code == 200
    data = response.json()
    assert data[0]["id"] == prediction.id
    assert data[0]["inference_time_ms"] == 12.5
    assert data[0]["is_low_confidence"] is False


def test_get_existing_disease_slug_returns_database_data(client, db_session):
    disease = create_disease(db_session)

    response = client.get(f"/api/v1/diseases/{disease.slug}")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == disease.name
    assert data["slug"] == disease.slug
    assert data["description"] == disease.description
    assert data["symptoms"] == disease.symptoms
    assert data["causes"] == disease.causes
    assert data["prevention"] == disease.prevention
    assert data["severity_level"] == disease.severity_level
    assert "not a replacement for diagnosis" in data["disclaimer"]


def test_get_unknown_disease_slug_returns_404(client):
    response = client.get("/api/v1/diseases/unknown")

    assert response.status_code == 404
    assert response.json()["detail"] == "Disease not found"


def test_get_disease_recommendations_are_returned_in_order(client, db_session):
    create_disease(db_session)

    response = client.get("/api/v1/diseases/rust")

    assert response.status_code == 200
    assert response.json()["recommendations"] == [
        "Confirm symptoms on multiple leaves.",
        "Consult a local agricultural expert.",
        "Improve orchard airflow where practical.",
    ]


def test_get_disease_keeps_backward_compatible_fields(client, db_session):
    create_disease(db_session)

    response = client.get("/api/v1/diseases/rust")

    assert response.status_code == 200
    data = response.json()
    for field in ["name", "slug", "description", "recommendations", "disclaimer"]:
        assert field in data
