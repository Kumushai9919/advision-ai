#!/usr/bin/env python3
"""
Thread-safe Message Producer for Face Recognition System
"""

import pika
import json
import uuid
import time
import os
import logging
import threading
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from queue import Queue, Empty
from src.core.config import get_settings

settings = get_settings()

@dataclass
class ProducerConfig:
    """Configuration for Message Producer"""
    host: str = settings.RABBITMQ_HOST
    port: int = settings.RABBITMQ_PORT
    username: str = settings.RABBITMQ_USERNAME
    password: str = settings.RABBITMQ_PASSWORD
    vhost: str = settings.RABBITMQ_VHOST
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
    Thread-safe Message Producer for face recognition workers
    Each instance maintains its own connection and response handling
    """
    
    def __init__(self, config: Optional[ProducerConfig] = None):
        self.config = config or ProducerConfig()
        self.connection = None
        self.channel = None
        self.response_queue = None
        self.logger = logging.getLogger(f'message_producer_{threading.current_thread().name}')
        
        # ✅ Thread-safe response handling
        self.pending_responses = {}  # correlation_id -> Queue
        self.lock = threading.Lock()
        self.consumer_tag = None
        
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
                )
                
                self.connection = pika.BlockingConnection(params)
                self.channel = self.connection.channel()
                
                # Create exclusive response queue for this producer instance
                result = self.channel.queue_declare(queue='', exclusive=True)
                self.response_queue = result.method.queue
                
                # ✅ Start consuming responses with callback
                self.consumer_tag = self.channel.basic_consume(
                    queue=self.response_queue,
                    on_message_callback=self._on_response,
                    auto_ack=True
                )
                
                self.logger.info(f"Connected successfully. Response queue: {self.response_queue}")
                return
                
            except Exception as e:
                self.logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (2 ** attempt))
                else:
                    raise ConnectionError(f"Failed to connect after {self.config.max_retries} attempts: {e}")

    def _on_response(self, ch, method, properties, body):
        """✅ Callback for handling responses - thread-safe"""
        correlation_id = properties.correlation_id
        
        with self.lock:
            if correlation_id in self.pending_responses:
                response_queue = self.pending_responses[correlation_id]
                try:
                    response = json.loads(body.decode())
                    response_queue.put(response)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to decode response: {e}")
                    response_queue.put({'status': 'error', 'error': f'Invalid JSON: {e}'})

    def _ensure_connection(self):
        """Ensure connection is alive, reconnect if needed"""
        if not self.connection or self.connection.is_closed:
            self.logger.warning("Connection lost, reconnecting...")
            self._setup_connection()
        elif not self.channel or self.channel.is_closed:
            self.logger.warning("Channel lost, reopening...")
            self._setup_connection()

    def _send_message(self, exchange: str, routing_key: str, message: dict, wait_for_response: bool = True) -> Optional[dict]:
        """✅ Thread-safe message sending"""
        correlation_id = str(uuid.uuid4())
        response_queue = Queue() if wait_for_response else None
        
        try:
            self._ensure_connection()
            
            # Register response queue
            if wait_for_response:
                with self.lock:
                    self.pending_responses[correlation_id] = response_queue
            
            # Add message metadata
            enhanced_message = {
                **message,
                'producer_id': f"producer-{threading.current_thread().name}",
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
                    delivery_mode=2,
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
            return self._wait_for_response(correlation_id, response_queue)
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            # Cleanup
            if wait_for_response:
                with self.lock:
                    self.pending_responses.pop(correlation_id, None)
            raise ProducerError(f"Message sending failed: {e}")

    def _wait_for_response(self, correlation_id: str, response_queue: Queue) -> dict:
        """✅ Thread-safe response waiting"""
        start_time = time.time()
        
        try:
            while True:
                elapsed = time.time() - start_time
                if elapsed > self.config.timeout:
                    raise TimeoutError(f"Request timed out after {self.config.timeout}s")
                
                # ✅ Process incoming messages (non-blocking)
                self.connection.process_data_events(time_limit=0.1)
                
                # Check if response arrived
                try:
                    response = response_queue.get(timeout=0.1)
                    
                    processing_time = int(time.time() * 1000) - response.get('sent_at', 0)
                    self.logger.info(f"Response received (processing time: {processing_time}ms)")
                    
                    if response.get('status') == 'error':
                        error_msg = response.get('error', 'Unknown error')
                        raise ProducerError(f"Worker error: {error_msg}")
                    
                    return response
                    
                except Empty:
                    continue
                    
        finally:
            # Cleanup
            with self.lock:
                self.pending_responses.pop(correlation_id, None)

    # ✅ All your existing methods remain the same
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
    
    # ... (rest of your methods remain the same)

    def close(self):
        """Close connection gracefully"""
        try:
            if self.consumer_tag and self.channel and not self.channel.is_closed:
                self.channel.basic_cancel(self.consumer_tag)
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