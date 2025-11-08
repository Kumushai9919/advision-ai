#!/usr/bin/env python3
"""
Message Producer API for Face Recognition System
Provides a clean interface for backend services to send messages to workers
"""

import pika
import json
import uuid
import time
import os
import logging
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager
from dotenv import load_dotenv, find_dotenv


load_dotenv(dotenv_path=find_dotenv())

@dataclass
class ProducerConfig:
    """Configuration for Message Producer"""
    host: str = 'localhost'
    port: int = 5672
    username: str = 'face_user'
    password: str = 'secure_password'
    vhost: str = '/face_recognition'
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    heartbeat: int = 600
    blocked_connection_timeout: int = 300

class ProducerError(Exception):
    """Base exception for Message Producer"""
    pass

class ConnectionError(ProducerError):
    """Connection-related errors"""
    pass

class TimeoutError(ProducerError):
    """Timeout-related errors"""
    pass

class MessageProducer:
    """
    Message Producer for sending tasks to face recognition workers
    
    Handles both:
    - Management tasks (fanout to all workers for cache sync)
    - Processing tasks (single worker for face operations)
    """
    
    def __init__(self, config: Optional[ProducerConfig] = None):
        self.config = config or ProducerConfig()
        self.connection = None
        self.channel = None
        self.response_queue = None
        self.logger = logging.getLogger('message_producer')
        self._setup_connection()
        
    def _setup_connection(self):
        """Setup RabbitMQ connection with resilience"""
        for attempt in range(self.config.max_retries):
            try:
                self.logger.info(f"Connecting to RabbitMQ (attempt {attempt + 1}/{self.config.max_retries})")
                
                params = pika.ConnectionParameters(
                    host=self.config.host,
                    port=self.config.port,
                    virtual_host=self.config.vhost,
                    credentials=pika.PlainCredentials(self.config.username, self.config.password),
                    heartbeat=self.config.heartbeat,
                    blocked_connection_timeout=self.config.blocked_connection_timeout,
                    retry_delay=self.config.retry_delay
                )
                
                self.connection = pika.BlockingConnection(params)
                self.channel = self.connection.channel()
                
                # Create temporary response queue for this client
                result = self.channel.queue_declare(queue='', exclusive=True)
                self.response_queue = result.method.queue
                
                self.logger.info(f"Connected successfully. Response queue: {self.response_queue}")
                return
                
            except Exception as e:
                self.logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (2 ** attempt))
                else:
                    raise ConnectionError(f"Failed to connect after {self.config.max_retries} attempts: {e}")

    def _ensure_connection(self):
        """Ensure connection is alive, reconnect if needed"""
        if not self.connection or self.connection.is_closed:
            self.logger.warning("Connection lost, reconnecting...")
            self._setup_connection()
        elif not self.channel or self.channel.is_closed:
            self.logger.warning("Channel lost, reopening...")
            self.channel = self.connection.channel()
            result = self.channel.queue_declare(queue='', exclusive=True)
            self.response_queue = result.method.queue

    def _send_message(self, exchange: str, routing_key: str, message: dict, wait_for_response: bool = True) -> Optional[dict]:
        """Send message and optionally wait for response"""
        correlation_id = str(uuid.uuid4())
        
        try:
            self._ensure_connection()
            
            # Add message metadata
            enhanced_message = {
                **message,
                'producer_id': f"producer-{os.getpid()}",
                'sent_at': int(time.time() * 1000),
                'correlation_id': correlation_id
            }
            
            # Publish message
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=json.dumps(enhanced_message),
                properties=pika.BasicProperties(
                    reply_to=self.response_queue if wait_for_response else None,
                    correlation_id=correlation_id,
                    delivery_mode=2,  # Persistent
                    content_type='application/json',
                    timestamp=int(time.time()),
                    app_id='message_producer',
                    message_id=str(uuid.uuid4())
                )
            )
            
            self.logger.info(f"Message sent to {exchange}/{routing_key} (CID: {correlation_id})")
            
            if not wait_for_response:
                return {'status': 'sent', 'correlation_id': correlation_id}
            
            # Wait for response
            return self._wait_for_response(correlation_id)
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            raise ProducerError(f"Message sending failed: {e}")

    def _wait_for_response(self, correlation_id: str) -> dict:
        """Wait for response with timeout"""
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > self.config.timeout:
                raise TimeoutError(f"Request timed out after {self.config.timeout}s")
            
            self._ensure_connection()
            
            method_frame, header_frame, body = self.channel.basic_get(
                queue=self.response_queue, 
                auto_ack=True
            )
            
            if method_frame and header_frame.correlation_id == correlation_id:
                try:
                    response = json.loads(body.decode())
                    processing_time = int(time.time() * 1000) - response.get('sent_at', 0)
                    self.logger.info(f"Response received (processing time: {processing_time}ms)")
                    
                    if response.get('status') == 'error':
                        error_msg = response.get('error', 'Unknown error')
                        raise ProducerError(f"Worker error: {error_msg}")
                    
                    return response
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to decode response: {e}")
                    raise ProducerError(f"Invalid response format: {e}")
            
            time.sleep(0.05)

    # Management Operations (FANOUT - All Workers)
    def create_company(self, company_id: str) -> bool:
        """Create company - synced across all workers"""
        message = {
            "task_id": str(uuid.uuid4()),
            "task_type": "create_company",
            "timestamp": int(time.time()),
            "parameters": {"company_id": company_id}
        }
        
        response = self._send_message('cache_updates', '', message)
        return response['result']['success']

    def delete_company(self, company_id: str) -> bool:
        """Delete company - synced across all workers"""
        message = {
            "task_id": str(uuid.uuid4()),
            "task_type": "delete_company",
            "timestamp": int(time.time()),
            "parameters": {"company_id": company_id}
        }
        
        response = self._send_message('cache_updates', '', message)
        return response['result']['success']

    def create_user(self, company_id: str, user_id: str, face_id: str, image_base64: str) -> List[float]:
        """Create user - synced across all workers"""
        message = {
            "task_id": str(uuid.uuid4()),
            "task_type": "create_user",
            "timestamp": int(time.time()),
            "parameters": {
                "company_id": company_id,
                "user_id": user_id,
                "face_id": face_id,
                "image_base64": image_base64
            }
        }
        
        response = self._send_message('cache_updates', '', message)
        return response['result']['embedding']
    
    def delete_user(self, company_id: str, user_id: str) -> bool:
        """Delete user - synced across all workers"""
        message = {
            "task_id": str(uuid.uuid4()),
            "task_type": "delete_user",
            "timestamp": int(time.time()),
            "parameters": {"company_id": company_id, "user_id": user_id}
        }
        
        response = self._send_message('cache_updates', '', message)
        return response['result']['success']
    
    def add_face(self, company_id: str, user_id: str, face_id: str, image_base64: str) -> List[float]:
        """Add face to user - synced across all workers"""
        message = {
            "task_id": str(uuid.uuid4()),
            "task_type": "add_face",
            "timestamp": int(time.time()),
            "parameters": {
                "company_id": company_id,
                "user_id": user_id,
                "face_id": face_id,
                "image_base64": image_base64
            }
        }
        
        response = self._send_message('cache_updates', '', message)
        return response['result']['embedding']
    
    def delete_face(self, company_id: str, user_id: str, face_id: str) -> bool:
        """Delete face - synced across all workers"""
        message = {
            "task_id": str(uuid.uuid4()),
            "task_type": "delete_face",
            "timestamp": int(time.time()),
            "parameters": {
                "company_id": company_id,
                "user_id": user_id,
                "face_id": face_id
            }
        }
        
        response = self._send_message('cache_updates', '', message)
        return response['result']['success']
    
    # Processing Operations (SINGLE WORKER)
    def recognize_face(self, company_id: str, image_base64: str) -> Tuple[Optional[str], float, List[int]]:
        """Recognize face in image"""
        message = {
            "task_id": str(uuid.uuid4()),
            "task_type": "face_recognition",
            "timestamp": int(time.time()),
            "parameters": {
                "company_id": company_id,
                "image_base64": image_base64
            }
        }
        
        response = self._send_message('face_tasks', 'face_recognition', message)
        result = response['result']
        return result.get('user_id'), result['confidence'], result['bbox']
    
    def detect_faces(self, image_base64: str) -> Tuple[int, List[List[int]]]:
        """Detect faces in image"""
        message = {
            "task_id": str(uuid.uuid4()),
            "task_type": "face_detection",
            "timestamp": int(time.time()),
            "parameters": {"image_base64": image_base64}
        }
        
        response = self._send_message('face_tasks', 'face_detection', message)
        result = response['result']
        return result['faces_detected'], result['bboxes']

    def generate_embedding(self, image_base64: str) -> List[float]:
        """Generate face embedding from image"""
        message = {
            "task_id": str(uuid.uuid4()),
            "task_type": "face_embedding", 
            "timestamp": int(time.time()),
            "parameters": {"image_base64": image_base64}
        }
        
        response = self._send_message('face_tasks', 'face_embedding', message)
        return response['result']['embedding']

    def get_user_faces(self, company_id: str, user_id: str) -> List[str]:
        """Get list of face IDs for a user"""
        message = {
            "task_id": str(uuid.uuid4()),
            "task_type": "get_user_faces",
            "timestamp": int(time.time()),
            "parameters": {"company_id": company_id, "user_id": user_id}
        }
        
        response = self._send_message('face_tasks', 'get_user_faces', message)
        return response['result']['face_ids']

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get worker cache statistics"""
        message = {
            "task_id": str(uuid.uuid4()),
            "task_type": "get_cache_stats",
            "timestamp": int(time.time()),
            "parameters": {}
        }
        
        response = self._send_message('face_tasks', 'get_cache_stats', message)
        return response['result']

    def health_check(self) -> Dict[str, Any]:
        """Check system health"""
        message = {
            "task_id": str(uuid.uuid4()),
            "task_type": "health_check",
            "timestamp": int(time.time()),
            "parameters": {}
        }
        
        try:
            start_time = time.time()
            response = self._send_message('face_tasks', 'health_check', message)
            end_time = time.time()
            
            return {
                'status': 'healthy',
                'response_time_ms': int((end_time - start_time) * 1000),
                'worker_info': response.get('result', {})
            }
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}

    # Utility Methods
    def send_fire_and_forget(self, exchange: str, routing_key: str, message: dict):
        """Send message without waiting for response"""
        return self._send_message(exchange, routing_key, message, wait_for_response=False)

    def close(self):
        """Close connection gracefully"""
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            self.logger.info("Connection closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing connection: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# Configuration helper
def get_config_from_env() -> ProducerConfig:
    """Load configuration from environment variables"""
    return ProducerConfig(
        host=os.getenv('RABBITMQ_HOST', 'localhost'),
        port=int(os.getenv('RABBITMQ_PORT', '5672')),
        username=os.getenv('RABBITMQ_USER', 'face_user'),
        password=os.getenv('RABBITMQ_PASS', 'secure_password'),
        vhost=os.getenv('RABBITMQ_VHOST', '/face_recognition'),
        timeout=int(os.getenv('PUBLISHER_TIMEOUT', '30')),
        max_retries=int(os.getenv('PUBLISHER_MAX_RETRIES', '3'))
    )