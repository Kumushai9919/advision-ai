#!/usr/bin/env python3
"""
Message Consumer API for Face Recognition System
Provides a clean interface for worker services to consume and process messages
"""

import pika
import json
import time
import threading
import os
import signal
import sys
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
# from contextmanager import contextmanager
from contextlib import contextmanager
from dotenv import load_dotenv, find_dotenv


load_dotenv(dotenv_path=find_dotenv())

@dataclass
class ConsumerConfig:
    """Configuration for Message Consumer"""
    host: str = 'localhost'
    port: int = 5672
    username: str = 'face_user'
    password: str = 'secure_password'
    vhost: str = '/face_recognition'
    max_retries: int = 5
    retry_delay: float = 2.0
    heartbeat: int = 600
    prefetch_count: int = 1
    processing_timeout: float = 30.0
    log_level: str = 'INFO'

class ConsumerError(Exception):
    """Base consumer exception"""
    pass

class ProcessingError(ConsumerError):
    """Processing-related errors"""
    pass

class TaskHandler(ABC):
    """Abstract base class for task handlers"""
    
    @abstractmethod
    def handle_task(self, task_type: str, parameters: dict) -> dict:
        """Handle a specific task and return result"""
        pass
    
    @abstractmethod
    def get_supported_tasks(self) -> list:
        """Return list of supported task types"""
        pass

class MessageConsumer:
    """
    Message Consumer for processing face recognition tasks
    
    Handles both:
    - Management tasks (fanout from all producers for cache sync)
    - Processing tasks (single consumer for face operations)
    """
    
    def __init__(self, worker_id: str, config: Optional[ConsumerConfig] = None):
        self.worker_id = worker_id
        self.config = config or ConsumerConfig()
        self.connection = None
        self.channel = None
        self.management_queue = None
        self.is_running = False
        self.shutdown_event = threading.Event()
        self.task_handlers: Dict[str, TaskHandler] = {}
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(f'message_consumer.{worker_id}')
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        # Connect to RabbitMQ
        self._setup_connection()
        
    def _setup_logging(self):
        """Setup comprehensive logging"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - [%(worker_id)s] %(message)s'
        
        class ContextualFormatter(logging.Formatter):
            def __init__(self, fmt, worker_id):
                super().__init__(fmt)
                self.worker_id = worker_id
            
            def format(self, record):
                if not hasattr(record, 'worker_id'):
                    record.worker_id = self.worker_id
                return super().format(record)
        
        formatter = ContextualFormatter(log_format, self.worker_id)
        
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.log_level.upper()))
        root_logger.handlers.clear()
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Reduce pika logging noise
        logging.getLogger('pika').setLevel(logging.WARNING)
        
    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.warning(f"Signal received: {signum} - Initiating graceful shutdown...")
        self.shutdown_event.set()
        
    def _setup_connection(self):
        """Setup RabbitMQ connection with resilience"""
        self.logger.info("Setting up RabbitMQ connection...")
        
        for attempt in range(self.config.max_retries):
            try:
                self.logger.info(f"Connection attempt {attempt + 1}/{self.config.max_retries}")
                
                params = pika.ConnectionParameters(
                    host=self.config.host,
                    port=self.config.port,
                    virtual_host=self.config.vhost,
                    credentials=pika.PlainCredentials(self.config.username, self.config.password),
                    heartbeat=self.config.heartbeat,
                    retry_delay=self.config.retry_delay
                )
                
                self.connection = pika.BlockingConnection(params)
                self.channel = self.connection.channel()
                
                self.logger.info("RabbitMQ connection established successfully")
                
                # Set QoS
                self.channel.basic_qos(prefetch_count=self.config.prefetch_count)
                
                # Setup consumers
                self._setup_consumers()
                
                return
                
            except Exception as e:
                self.logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    self.logger.warning(f"Retrying connection in {delay}s...")
                    time.sleep(delay)
                else:
                    error_msg = f"Failed to connect after {self.config.max_retries} attempts"
                    self.logger.error(error_msg)
                    raise ConsumerError(error_msg)

    def _setup_consumers(self):
        """Setup message consumers"""
        self.logger.info("Setting up message consumers...")
        
        try:
            # Processing tasks consumer (SINGLE WORKER)
            self.channel.basic_consume(
                queue='face_processing_tasks',
                on_message_callback=self._handle_processing_task,
                auto_ack=False
            )
            self.logger.info("Processing consumer setup: face_processing_tasks")
            
            # Management fanout consumer (ALL WORKERS)
            result = self.channel.queue_declare(queue='', exclusive=True)
            self.management_queue = result.method.queue
            
            self.channel.queue_bind(
                exchange='cache_updates',
                queue=self.management_queue
            )
            
            self.channel.basic_consume(
                queue=self.management_queue,
                on_message_callback=self._handle_management_fanout,
                auto_ack=False
            )
            self.logger.info(f"Fanout consumer setup: {self.management_queue}")
            
            # Legacy management consumer (backward compatibility)
            self.channel.basic_consume(
                queue='face_management_tasks',
                on_message_callback=self._handle_management_direct,
                auto_ack=False
            )
            self.logger.info("Direct management consumer setup: face_management_tasks")
            
        except Exception as e:
            self.logger.error(f"Failed to setup consumers: {e}")
            raise

    def register_task_handler(self, handler: TaskHandler):
        """Register a task handler for specific task types"""
        supported_tasks = handler.get_supported_tasks()
        for task_type in supported_tasks:
            self.task_handlers[task_type] = handler
            self.logger.info(f"Registered handler for task type: {task_type}")

    def _handle_processing_task(self, ch, method, properties, body):
        """Handle processing tasks (single worker)"""
        correlation_id = properties.correlation_id or 'unknown'
        delivery_tag = method.delivery_tag
        
        self.logger.info(f"Processing task received (CID: {correlation_id})")
        
        try:
            message = json.loads(body.decode())
            task_type = message.get('task_type')
            task_id = message.get('task_id')
            parameters = message.get('parameters', {})
            
            self.logger.info(f"Task: {task_type} (ID: {task_id})")
            
            start_time = time.time()
            
            # Process with registered handler
            if task_type in self.task_handlers:
                response = self.task_handlers[task_type].handle_task(task_type, parameters)
            else:
                response = {'status': 'error', 'error': f'Unknown task type: {task_type}'}
            
            processing_time = int((time.time() - start_time) * 1000)
            self.logger.info(f"Task completed in {processing_time}ms")
            
            # Send response
            if properties.reply_to:
                self._send_response(properties.reply_to, correlation_id, response)
            
            ch.basic_ack(delivery_tag=delivery_tag)
            
        except Exception as e:
            self.logger.error(f"Processing error: {e}")
            error_response = {'status': 'error', 'error': str(e)}
            if properties.reply_to:
                self._send_response(properties.reply_to, correlation_id, error_response)
            ch.basic_nack(delivery_tag=delivery_tag, requeue=False)

    def _handle_management_fanout(self, ch, method, properties, body):
        """Handle management tasks from fanout exchange (all workers)"""
        correlation_id = properties.correlation_id or 'unknown'
        delivery_tag = method.delivery_tag
        
        self.logger.info(f"Fanout management message received (CID: {correlation_id})")
        
        try:
            message = json.loads(body.decode())
            task_type = message.get('task_type')
            parameters = message.get('parameters', {})
            
            start_time = time.time()
            
            # Process with registered handler
            if task_type in self.task_handlers:
                response = self.task_handlers[task_type].handle_task(task_type, parameters)
            else:
                response = {'status': 'error', 'error': f'Unknown management task: {task_type}'}
            
            processing_time = int((time.time() - start_time) * 1000)
            self.logger.info(f"Fanout task completed in {processing_time}ms")
            
            # Send response (publisher takes first response)
            if properties.reply_to:
                self._send_response(properties.reply_to, correlation_id, response)
            
            ch.basic_ack(delivery_tag=delivery_tag)
            
        except Exception as e:
            self.logger.error(f"Fanout management error: {e}")
            error_response = {'status': 'error', 'error': str(e)}
            if properties.reply_to:
                self._send_response(properties.reply_to, correlation_id, error_response)
            ch.basic_nack(delivery_tag=delivery_tag, requeue=False)

    def _handle_management_direct(self, ch, method, properties, body):
        """Handle management tasks from direct queue (backward compatibility)"""
        correlation_id = properties.correlation_id or 'unknown'
        delivery_tag = method.delivery_tag
        
        self.logger.info(f"Direct management message received (CID: {correlation_id})")
        
        try:
            message = json.loads(body.decode())
            task_type = message.get('task_type')
            parameters = message.get('parameters', {})
            
            start_time = time.time()
            
            # Process with registered handler
            if task_type in self.task_handlers:
                response = self.task_handlers[task_type].handle_task(task_type, parameters)
            else:
                response = {'status': 'error', 'error': f'Unknown direct management task: {task_type}'}
            
            processing_time = int((time.time() - start_time) * 1000)
            self.logger.info(f"Direct management task completed in {processing_time}ms")
            
            # Send response
            if properties.reply_to:
                self._send_response(properties.reply_to, correlation_id, response)
            
            ch.basic_ack(delivery_tag=delivery_tag)
            
        except Exception as e:
            self.logger.error(f"Direct management error: {e}")
            error_response = {'status': 'error', 'error': str(e)}
            if properties.reply_to:
                self._send_response(properties.reply_to, correlation_id, error_response)
            ch.basic_nack(delivery_tag=delivery_tag, requeue=False)

    def _send_response(self, reply_to: str, correlation_id: str, response: dict):
        """Send response back to producer"""
        try:
            enhanced_response = {
                **response,
                'worker_id': self.worker_id,
                'processed_at': int(time.time() * 1000),
                'correlation_id': correlation_id
            }
            
            self.channel.basic_publish(
                exchange='',
                routing_key=reply_to,
                body=json.dumps(enhanced_response),
                properties=pika.BasicProperties(
                    correlation_id=correlation_id,
                    content_type='application/json',
                    app_id=f'message_consumer_{self.worker_id}'
                )
            )
            self.logger.debug(f"Response sent (CID: {correlation_id})")
            
        except Exception as e:
            self.logger.error(f"Failed to send response: {e}")

    def start_consuming(self):
        """Start consuming messages"""
        self.start_time = time.time()
        self.is_running = True
        
        self.logger.info(f"Starting message consumer: {self.worker_id}")
        self.logger.info(f"Worker configuration: {self.config.host}:{self.config.port}")
        self.logger.info("Consumer is ready to process messages")
        
        try:
            while self.is_running and not self.shutdown_event.is_set():
                try:
                    self.connection.process_data_events(time_limit=1.0)
                    
                except pika.exceptions.AMQPConnectionError:
                    self.logger.warning("Connection lost, attempting reconnection...")
                    try:
                        self._setup_connection()
                        self.logger.info("Reconnection successful")
                    except Exception as e:
                        self.logger.error(f"Reconnection failed: {e}")
                        time.sleep(5.0)
                        
                except Exception as e:
                    self.logger.error(f"Unexpected error: {e}")
                    time.sleep(1.0)
                    
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Fatal error in consumer loop: {e}")
        finally:
            self._shutdown()

    def stop_consuming(self):
        """Stop consuming messages gracefully"""
        self.logger.info("Stopping message consumer...")
        self.shutdown_event.set()

    def _shutdown(self):
        """Graceful shutdown"""
        self.logger.info("Initiating graceful shutdown...")
        self.is_running = False
        
        try:
            if self.channel and not self.channel.is_closed:
                self.logger.info("Stopping consumers...")
                self.channel.stop_consuming()
                
            if self.connection and not self.connection.is_closed:
                self.logger.info("Closing connection...")
                self.connection.close()
                
            uptime = int(time.time() - getattr(self, 'start_time', time.time()))
            self.logger.info(f"Shutdown completed successfully (uptime: {uptime}s)")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    def get_stats(self) -> dict:
        """Get consumer statistics"""
        uptime = int(time.time() - getattr(self, 'start_time', time.time()))
        return {
            'worker_id': self.worker_id,
            'uptime_seconds': uptime,
            'registered_handlers': len(self.task_handlers),
            'supported_tasks': list(self.task_handlers.keys()),
            'status': 'running' if self.is_running else 'stopped',
            'management_queue': self.management_queue
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._shutdown()

# Configuration helper
def get_config_from_env() -> ConsumerConfig:
    """Load configuration from environment variables"""
    return ConsumerConfig(
        host=os.getenv('RABBITMQ_HOST', 'localhost'),
        port=int(os.getenv('RABBITMQ_PORT', '5672')),
        username=os.getenv('RABBITMQ_USER', 'face_user'),
        password=os.getenv('RABBITMQ_PASS', 'secure_password'),
        vhost=os.getenv('RABBITMQ_VHOST', '/face_recognition'),
        max_retries=int(os.getenv('WORKER_MAX_RETRIES', '5')),
        prefetch_count=int(os.getenv('WORKER_PREFETCH_COUNT', '1')),
        processing_timeout=float(os.getenv('WORKER_PROCESSING_TIMEOUT', '30.0')),
        log_level=os.getenv('LOG_LEVEL', 'INFO')
    )