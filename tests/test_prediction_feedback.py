import os
import asyncio
import io

os.environ["DEBUG"] = "false"
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta, timezone

from app.api.dependencies import get_current_user
from app.core.security import create_access_token
from app.db.database import get_db
from app.main import app as fastapi_app
from app.models.base import Base
from app.models.disease import Disease, DiseaseRecommendation
from app.models.prediction import Prediction
from app.models.prediction_feedback import PredictionFeedback
from app.models.user import User
from app.schemas.prediction import GradCamExplanationResponse
from app.services.image_quality_service import assess_image_quality
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


def create_prediction(
    db_session,
    user: User,
    predicted_class: str = "rust",
    confidence: float = 0.93,
    inference_time_ms: float = 12.5,
    is_low_confidence: bool = False,
    model_version: str = "test-model",
    created_at: datetime = None,
    image_quality_score: float = 0.86,
    is_quality_acceptable: bool = True,
    quality_warnings_json: str = "[]",
) -> Prediction:
    prediction = Prediction(
        user_id=user.id,
        image_name="leaf.jpg",
        predicted_class=predicted_class,
        confidence=confidence,
        inference_time_ms=inference_time_ms,
        is_low_confidence=is_low_confidence,
        image_width=1024,
        image_height=768,
        image_brightness_score=128.45,
        image_contrast_score=52.1,
        image_blur_score=315.78,
        image_quality_score=image_quality_score,
        is_quality_acceptable=is_quality_acceptable,
        quality_warnings_json=quality_warnings_json,
        scores_json='{"healthy": 0.01, "rust": 0.93, "scab": 0.06}',
        model_version=model_version,
        created_at=created_at or datetime.now(timezone.utc),
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


def test_create_prediction_feedback_rejects_corrected_class_when_correct(client, db_session):
    user = create_user(db_session, "owner@example.com")
    prediction = create_prediction(db_session, user)

    response = client.post(
        f"/api/v1/predictions/{prediction.id}/feedback",
        headers=auth_headers(user),
        json={"is_correct": True, "corrected_class": "rust"},
    )

    assert response.status_code == 422


def test_good_quality_synthetic_image_is_acceptable():
    quality = assess_image_quality(create_good_quality_image())

    assert quality.width == 256
    assert quality.height == 256
    assert quality.is_quality_acceptable is True
    assert quality.quality_warnings == []
    assert quality.quality_score == 1.0


def test_dark_image_returns_dark_warning():
    quality = assess_image_quality(Image.new("RGB", (256, 256), (10, 10, 10)))

    assert quality.is_quality_acceptable is False
    assert "The image is too dark. Please use better lighting." in quality.quality_warnings


def test_small_image_returns_low_resolution_warning():
    quality = assess_image_quality(Image.new("RGB", (100, 100), (128, 128, 128)))

    assert quality.is_quality_acceptable is False
    assert "The image resolution is low. Please upload a larger image." in quality.quality_warnings


def test_low_detail_image_returns_blur_warning():
    quality = assess_image_quality(Image.new("RGB", (256, 256), (128, 128, 128)))

    assert quality.is_quality_acceptable is False
    assert "The image appears blurry. Please retake the photo with a steady camera." in quality.quality_warnings


class DummyUploadFile:
    filename = "leaf.jpg"


async def fake_validate_and_open_image(file):
    return create_good_quality_image()


def create_good_quality_image(width: int = 256, height: int = 256) -> Image.Image:
    image = Image.new("RGB", (width, height), "white")
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            value = 60 if (x // 8 + y // 8) % 2 == 0 else 190
            pixels[x, y] = (value, value, value)
    return image


def image_file_tuple(image: Image.Image = None):
    image = image or create_good_quality_image()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return ("leaf.png", buffer, "image/png")


def mock_prediction_dependencies(monkeypatch):
    monkeypatch.setattr(prediction_service, "preprocess_image", lambda image: object())
    monkeypatch.setattr(
        prediction_service,
        "predict",
        lambda tensor: ("rust", 0.91, {"healthy": 0.01, "rust": 0.91, "scab": 0.08}),
    )
    monkeypatch.setattr(prediction_service.ml_manager, "model_version", "test-model")


def test_prediction_response_includes_latency_and_low_confidence(monkeypatch, db_session):
    user = create_user(db_session, "owner@example.com")

    monkeypatch.setattr(prediction_service, "validate_and_open_image", fake_validate_and_open_image)
    monkeypatch.setattr(prediction_service, "preprocess_image", lambda image: object())
    monkeypatch.setattr(
        prediction_service,
        "predict",
        lambda tensor: ("rust", 0.69, {"healthy": 0.05, "rust": 0.69, "scab": 0.26}),
    )
    perf_counter_values = iter([10.0, 10.123456])
    monkeypatch.setattr(prediction_service.time, "perf_counter", lambda: next(perf_counter_values))
    monkeypatch.setattr(prediction_service.ml_manager, "model_version", "test-model")

    response = asyncio.run(
        prediction_service.process_prediction(DummyUploadFile(), save_result=False, user=user, db=db_session)
    )

    assert response.inference_time_ms == 123.46
    assert response.is_low_confidence is True
    assert response.model_version == "test-model"
    assert response.predicted_class == "rust"
    assert response.confidence == 0.69
    assert response.scores == {"healthy": 0.05, "rust": 0.69, "scab": 0.26}
    assert response.supported_classes == ["healthy", "rust", "scab"]
    assert response.image_quality.width == 256
    assert response.image_quality.is_quality_acceptable is True
    assert response.warning == "The model confidence is low. Please retake the image under better lighting or consult an agricultural expert."
    assert response.explanation is None


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
    assert saved_prediction.image_width == 256
    assert saved_prediction.image_height == 256
    assert saved_prediction.image_quality_score is not None
    assert saved_prediction.is_quality_acceptable is True
    assert saved_prediction.quality_warnings_json == "[]"


def test_prediction_endpoint_without_explanation_returns_null(client, db_session, monkeypatch):
    user = create_user(db_session, "owner@example.com")
    mock_prediction_dependencies(monkeypatch)

    response = client.post(
        "/api/v1/predictions/",
        headers=auth_headers(user),
        data={"save_result": "false", "include_explanation": "false"},
        files={"file": image_file_tuple()},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["predicted_class"] == "rust"
    assert data["confidence"] == 0.91
    assert data["image_quality"]["is_quality_acceptable"] is True
    assert data["explanation"] is None


def test_prediction_endpoint_with_explanation_returns_gradcam_object(client, db_session, monkeypatch):
    user = create_user(db_session, "owner@example.com")
    mock_prediction_dependencies(monkeypatch)

    def fake_generate_gradcam_explanation(**kwargs):
        return GradCamExplanationResponse(
            method="Grad-CAM",
            target_class=kwargs["class_name"],
            target_layer="layer4",
            image_format="png",
            overlay_image_base64="overlay-base64",
            heatmap_image_base64="heatmap-base64",
            disclaimer="Grad-CAM is an approximate visual explanation of model attention and is not a replacement for expert agricultural diagnosis.",
            explanation_time_ms=12.34,
        )

    monkeypatch.setattr(prediction_service, "generate_gradcam_explanation", fake_generate_gradcam_explanation)
    monkeypatch.setattr(prediction_service.ml_manager, "is_loaded", True)
    monkeypatch.setattr(prediction_service.ml_manager, "model", object())
    monkeypatch.setattr(prediction_service.ml_manager, "device", "cpu")

    response = client.post(
        "/api/v1/predictions/",
        headers=auth_headers(user),
        data={"save_result": "false", "include_explanation": "true"},
        files={"file": image_file_tuple()},
    )

    assert response.status_code == 200
    explanation = response.json()["explanation"]
    assert explanation["method"] == "Grad-CAM"
    assert explanation["target_class"] == "rust"
    assert explanation["overlay_image_base64"] == "overlay-base64"
    assert explanation["heatmap_image_base64"] == "heatmap-base64"
    assert explanation["explanation_time_ms"] == 12.34


def test_prediction_endpoint_handles_gradcam_failure_gracefully(client, db_session, monkeypatch):
    user = create_user(db_session, "owner@example.com")
    mock_prediction_dependencies(monkeypatch)

    def failing_generate_gradcam_explanation(**kwargs):
        raise RuntimeError("Grad-CAM failed")

    monkeypatch.setattr(prediction_service, "generate_gradcam_explanation", failing_generate_gradcam_explanation)
    monkeypatch.setattr(prediction_service.ml_manager, "is_loaded", True)
    monkeypatch.setattr(prediction_service.ml_manager, "model", object())

    response = client.post(
        "/api/v1/predictions/",
        headers=auth_headers(user),
        data={"save_result": "false", "include_explanation": "true"},
        files={"file": image_file_tuple()},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["explanation"] is None
    assert "Grad-CAM explanation could not be generated for this image." in data["warning"]


def test_prediction_endpoint_invalid_image_keeps_existing_validation(client, db_session):
    user = create_user(db_session, "owner@example.com")
    invalid_file = ("leaf.png", io.BytesIO(b"not-an-image"), "image/png")

    response = client.post(
        "/api/v1/predictions/",
        headers=auth_headers(user),
        data={"save_result": "false", "include_explanation": "true"},
        files={"file": invalid_file},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is not a valid image"


def test_prediction_openapi_contains_include_explanation(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    openapi_schema = response.json()
    request_schema_ref = openapi_schema["paths"]["/api/v1/predictions/"]["post"]["requestBody"]["content"][
        "multipart/form-data"
    ]["schema"]["$ref"]
    request_schema_name = request_schema_ref.split("/")[-1]
    request_schema = openapi_schema["components"]["schemas"][request_schema_name]
    assert "include_explanation" in request_schema["properties"]


def test_history_returns_latency_and_low_confidence(client, db_session):
    user = create_user(db_session, "owner@example.com")
    prediction = create_prediction(db_session, user)

    response = client.get("/api/v1/history/", headers=auth_headers(user))

    assert response.status_code == 200
    data = response.json()
    assert data[0]["id"] == prediction.id
    assert data[0]["inference_time_ms"] == 12.5
    assert data[0]["is_low_confidence"] is False
    assert data[0]["image_quality"]["quality_score"] == 0.86
    assert data[0]["image_quality"]["is_quality_acceptable"] is True


def test_history_handles_old_records_without_quality_metadata(client, db_session):
    user = create_user(db_session, "owner@example.com")
    prediction = create_prediction(db_session, user)
    prediction.image_width = None
    prediction.image_height = None
    prediction.image_brightness_score = None
    prediction.image_contrast_score = None
    prediction.image_blur_score = None
    prediction.image_quality_score = None
    prediction.is_quality_acceptable = None
    prediction.quality_warnings_json = None
    db_session.commit()

    response = client.get("/api/v1/history/", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json()[0]["image_quality"] is None


def test_history_returns_newest_predictions_first(client, db_session):
    user = create_user(db_session, "owner@example.com")
    now = datetime.now(timezone.utc)
    older = create_prediction(
        db_session,
        user,
        predicted_class="healthy",
        created_at=now - timedelta(minutes=10),
    )
    newer = create_prediction(
        db_session,
        user,
        predicted_class="scab",
        created_at=now,
    )

    response = client.get("/api/v1/history/", headers=auth_headers(user))

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert ids == [newer.id, older.id]


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


def test_analytics_summary_requires_authentication(client):
    response = client.get("/api/v1/analytics/summary")

    assert response.status_code == 401


def test_analytics_summary_empty_history(client, db_session):
    user = create_user(db_session, "owner@example.com")

    response = client.get("/api/v1/analytics/summary", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json() == {
        "total_predictions": 0,
        "class_distribution": {},
        "average_confidence": None,
        "low_confidence_count": 0,
        "low_confidence_rate": 0.0,
        "average_inference_time_ms": None,
        "average_image_quality_score": None,
        "low_quality_count": 0,
        "low_quality_rate": 0.0,
        "latest_prediction": None,
        "model_version_distribution": {},
    }


def test_analytics_summary_multiple_predictions_excludes_other_users(client, db_session):
    user = create_user(db_session, "owner@example.com")
    other_user = create_user(db_session, "other@example.com")
    now = datetime.now(timezone.utc)
    create_prediction(
        db_session,
        user,
        predicted_class="healthy",
        confidence=0.9,
        inference_time_ms=100,
        is_low_confidence=False,
        image_quality_score=0.9,
        is_quality_acceptable=True,
        model_version="resnet50_v1",
        created_at=now - timedelta(minutes=3),
    )
    create_prediction(
        db_session,
        user,
        predicted_class="rust",
        confidence=0.6,
        inference_time_ms=200,
        is_low_confidence=True,
        image_quality_score=0.4,
        is_quality_acceptable=False,
        model_version="resnet50_v1",
        created_at=now - timedelta(minutes=2),
    )
    latest = create_prediction(
        db_session,
        user,
        predicted_class="scab",
        confidence=0.8,
        inference_time_ms=300,
        is_low_confidence=False,
        image_quality_score=0.8,
        is_quality_acceptable=True,
        model_version="resnet50_v2",
        created_at=now - timedelta(minutes=1),
    )
    create_prediction(
        db_session,
        other_user,
        predicted_class="rust",
        confidence=0.1,
        inference_time_ms=999,
        is_low_confidence=True,
        model_version="other-model",
        created_at=now,
    )

    response = client.get("/api/v1/analytics/summary", headers=auth_headers(user))

    assert response.status_code == 200
    data = response.json()
    assert data["total_predictions"] == 3
    assert data["class_distribution"] == {"healthy": 1, "rust": 1, "scab": 1}
    assert data["average_confidence"] == pytest.approx((0.9 + 0.6 + 0.8) / 3)
    assert data["low_confidence_count"] == 1
    assert data["low_confidence_rate"] == pytest.approx(1 / 3)
    assert data["average_inference_time_ms"] == pytest.approx(200)
    assert data["average_image_quality_score"] == pytest.approx(0.7)
    assert data["low_quality_count"] == 1
    assert data["low_quality_rate"] == pytest.approx(1 / 3)
    assert data["model_version_distribution"] == {"resnet50_v1": 2, "resnet50_v2": 1}
    assert data["latest_prediction"]["id"] == latest.id
    assert data["latest_prediction"]["predicted_class"] == "scab"
    assert data["latest_prediction"]["confidence"] == 0.8
