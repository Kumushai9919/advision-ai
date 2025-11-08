"""
Face Recognition Broker Client Library

This package provides a simple API for backend developers to integrate
face recognition capabilities using RabbitMQ messaging.

Basic Usage:
    from broker.message_producer import MessageProducer

    with MessageProducer() as producer:
        # Create company
        producer.create_company("company_123")

        # Register user with face
        embedding = producer.create_user(
            company_id="company_123",
            user_id="john_doe",
            face_id="face_001",
            image_base64=base64_image
        )

        # Recognize face
        user_id, confidence, bbox = producer.recognize_face(
            company_id="company_123",
            image_base64=base64_image
        )

For detailed documentation, see README.MD
"""

from .message_producer import MessageProducer, ProducerConfig, ProducerError, get_config_from_env
from .message_consumer import MessageConsumer, ConsumerConfig, TaskHandler

__version__ = "1.0.0"

__all__ = [
    "MessageProducer",
    "ProducerConfig",
    "ProducerError",
    "MessageConsumer",
    "ConsumerConfig",
    "TaskHandler",
    "get_config_from_env",
]