import pytest

from src.service.face_service import FaceService


def test_validate_embedding_happy_path():
    # Arrange
    svc = FaceService(db=None)
    embedding = [0.1, 0.0, 1, 2.5]

    # Act
    normalized = svc.validate_embedding(embedding)

    # Assert
    assert isinstance(normalized, list)
    assert all(isinstance(x, float) for x in normalized)
    assert normalized == [0.1, 0.0, 1.0, 2.5]


def test_validate_embedding_empty_raises_value_error():
    svc = FaceService(db=None)

    with pytest.raises(ValueError) as exc:
        svc.validate_embedding([])

    assert "Embedding cannot be empty" in str(exc.value)


def test_validate_embedding_invalid_types_raises_value_error():
    svc = FaceService(db=None)

    # Strings in embedding should raise
    with pytest.raises(ValueError) as exc:
        svc.validate_embedding(["a", "b"])

    assert "Invalid embedding format" in str(exc.value)
