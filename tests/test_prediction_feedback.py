import os

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
from app.models.prediction import Prediction
from app.models.prediction_feedback import PredictionFeedback
from app.models.user import User


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
