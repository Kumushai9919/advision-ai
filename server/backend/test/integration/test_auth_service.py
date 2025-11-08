import base64
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.service.auth_service import AuthService
from src.core.exception import FaceNotDetectedError, UserNotFoundError, InternalError


class DummyDB:
    def __init__(self):
        self.committed = False
    def commit(self):
        self.committed = True
    def rollback(self):
        pass


def make_image_bytes():
    return b"\xff\xd8\xff\xdbdummyjpegdata"


def test_register_creates_face_and_uploads_and_returns_success(monkeypatch):
    db = DummyDB()

    # Mock dependencies created inside AuthService
    user = Mock()
    # Use a string uuid-like to match usage of str(user.id)
    user.id = "1d2f3a4b-0000-0000-0000-1234567890ab"
    user.user_id = "external-id"
    user.org_id = "org-1"

    # Mock UserService.get_or_create to return (user, True)
    mock_user_service = Mock()
    mock_user_service.get_or_create.return_value = (user, True)
    # Ensure _ensure_org_exists sees an existing org (non-empty list)
    mock_user_service.get_by_org.return_value = [user]

    # Mock message producer to return an embedding list
    mock_producer = Mock()
    mock_producer.create_user.return_value = [0.1, 0.2, 0.3]

    # Mock MinIoService to return an image URL
    mock_minio = Mock()
    mock_minio.upload_face_image.return_value = "http://minio/org-1/user-uuid/image.jpg"

    # Mock FaceService.create
    mock_face_service = Mock()
    mock_face_service.create.return_value = Mock()

    with patch("src.service.auth_service.UserService", return_value=mock_user_service), \
         patch("src.service.auth_service.FaceService", return_value=mock_face_service), \
         patch("src.service.auth_service.MinIoService", return_value=mock_minio), \
         patch("src.service.auth_service.message_producer_singleton") as mock_singleton:

        mock_singleton.get_producer.return_value = mock_producer

        svc = AuthService(db=db)

        image = make_image_bytes()
        resp = svc.register(image, "jpg", "external-id", "org-1")

        assert resp.success is True
        assert resp.data.user_id == "external-id"
        mock_face_service.create.assert_called_once()
        mock_minio.upload_face_image.assert_called_once()


def test_detect_raises_when_no_face(monkeypatch):
    db = DummyDB()

    mock_producer = Mock()
    mock_producer.recognize_face.return_value = (None, None, None)

    with patch("src.service.auth_service.message_producer_singleton") as mock_singleton, \
        patch("src.service.auth_service.UserService") as mock_user_service_class:

        mock_singleton.get_producer.return_value = mock_producer
        svc = AuthService(db=db)

        with pytest.raises(FaceNotDetectedError):
            svc.detect(b"imgdata", "org-1")


def test_detect_returns_user_when_found(monkeypatch):
    db = DummyDB()

    # Prepare a recognized user id that maps to User.id in DB
    recognized_user_db_id = "db-uuid"
    confidence = 0.95

    mock_producer = Mock()
    mock_producer.recognize_face.return_value = (recognized_user_db_id, confidence, None)

    # Mock UserService.get_by_id to return a user with external user_id
    user = Mock()
    user.user_id = "external-123"

    mock_user_service = Mock()
    mock_user_service.get_by_id.return_value = user
    mock_user_service.get_by_org.return_value = [user]

    with patch("src.service.auth_service.message_producer_singleton") as mock_singleton, \
         patch("src.service.auth_service.UserService", return_value=mock_user_service):

        mock_singleton.get_producer.return_value = mock_producer

        svc = AuthService(db=db)

        resp = svc.detect(b"imgdata", "org-1")

        assert resp.success is True
        assert resp.data.user_id == "external-123"
        assert resp.data.confidence == confidence
