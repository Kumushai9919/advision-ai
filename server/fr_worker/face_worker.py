#!/usr/bin/env python3
"""
Face Recognition Worker Service
Main entry point for the face recognition worker that processes messages from RabbitMQ
"""

import os
import sys
import argparse
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import signal
import time
from typing import Optional

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from broker package
from broker import MessageConsumer, ConsumerConfig
from broker.message_consumer import get_config_from_env
from face_task_handler import FaceTaskHandler


class FaceWorker:
    """
    Main Face Recognition Worker Service
    
    Combines MessageConsumer with FaceTaskHandler to create a complete
    worker service that can process face recognition tasks
    """
    
    def __init__(self, worker_id: str, host: Optional[str] = None, config: Optional[ConsumerConfig] = None):
        self.worker_id = worker_id
        self.config = config or get_config_from_env()
        
        # Override host if provided
        if host:
            self.config.host = host
        
        self.consumer = None
        self.task_handler = None
        self.logger = logging.getLogger(f'face_worker.{worker_id}')
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.warning(f"Received signal {signum}, shutting down gracefully...")
        if self.consumer:
            self.consumer.stop_consuming()
    
    def initialize(self):
        """Initialize the worker components"""
        self.logger.info(f"Initializing face worker: {self.worker_id}")
        
        try:
            # Create task handler
            self.task_handler = FaceTaskHandler(self.worker_id)
            self.logger.info("Face task handler created")
            
            # Create message consumer
            self.consumer = MessageConsumer(self.worker_id, self.config)
            self.logger.info("Message consumer created")
            
            # Register task handler with consumer
            self.consumer.register_task_handler(self.task_handler)
            self.logger.info("Task handler registered with consumer")
            
            supported_tasks = self.task_handler.get_supported_tasks()
            self.logger.info(f"Worker supports {len(supported_tasks)} task types: {supported_tasks}")
            
            self.logger.info(f"Face worker '{self.worker_id}' initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize worker: {e}")
            raise
    
    def start(self):
        """Start the worker service"""
        self.logger.info(f"Starting face worker service: {self.worker_id}")
        
        try:
            # Initialize if not already done
            if not self.consumer:
                self.initialize()
            
            # Log startup information
            self.logger.info("=" * 60)
            self.logger.info(f"Face Recognition Worker: {self.worker_id}")
            self.logger.info(f"RabbitMQ Host: {self.config.host}:{self.config.port}")
            self.logger.info(f"Virtual Host: {self.config.vhost}")
            self.logger.info(f"Prefetch Count: {self.config.prefetch_count}")
            self.logger.info(f"Log Level: {self.config.log_level}")
            self.logger.info("=" * 60)
            
            # Start consuming messages
            self.logger.info("Starting message consumption...")
            self.consumer.start_consuming()
            
        except KeyboardInterrupt:
            self.logger.info("Worker stopped by user")
        except Exception as e:
            self.logger.error(f"Worker failed: {e}")
            raise
        finally:
            self._cleanup()
    
    def stop(self):
        """Stop the worker service"""
        self.logger.info("Stopping face worker service...")
        if self.consumer:
            self.consumer.stop_consuming()
    
    def _cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up worker resources...")
        # Consumer handles its own cleanup
        self.logger.info("Worker cleanup completed")
    
    def get_stats(self) -> dict:
        """Get worker statistics"""
        stats = {
            'worker_id': self.worker_id,
            'status': 'running' if self.consumer and self.consumer.is_running else 'stopped'
        }
        
        if self.consumer:
            stats.update(self.consumer.get_stats())
        
        return stats


def setup_logging(log_level: str = 'INFO', log_dir: str = 'logs'):
    """Setup logging configuration with file output"""
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.handlers.clear()
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)
    
    # File handler with rotation (10MB per file, keep 5 files)
    file_handler = RotatingFileHandler(
        filename=log_path / 'face_worker.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(file_handler)
    
    # Error file handler - separate file for errors only
    error_handler = RotatingFileHandler(
        filename=log_path / 'face_worker_errors.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(error_handler)
    
    # Reduce pika logging noise
    logging.getLogger('pika').setLevel(logging.WARNING)
    
    logging.info(f"Logging initialized: level={log_level}, directory={log_dir}")


# Update parse_arguments() to add log directory option
def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Face Recognition Worker Service')
    
    parser.add_argument(
        '--worker-id',
        type=str,
        default=f'worker-{os.getpid()}',
        help='Unique worker ID (default: worker-{pid})'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        help='RabbitMQ host (overrides config/env)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        help='RabbitMQ port (overrides config/env)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default=os.getenv('LOG_LEVEL', 'INFO'),
        help='Logging level'
    )
    
    parser.add_argument(
        '--log-dir',
        type=str,
        default=os.getenv('LOG_DIR', 'logs'),
        help='Directory for log files (default: logs)'
    )
    
    parser.add_argument(
        '--prefetch-count',
        type=int,
        help='Number of messages to prefetch'
    )
    
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Run in test mode (exit after initialization)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Setup logging with file output
    setup_logging(args.log_level, args.log_dir)
    logger = logging.getLogger('face_worker.main')
    
    logger.info("Starting Face Recognition Worker Service")
    logger.info(f"Worker ID: {args.worker_id}")
    logger.info(f"Log Level: {args.log_level}")
    logger.info(f"Log Directory: {args.log_dir}")
    
    try:
        # Create worker configuration
        config = get_config_from_env()
        
        # Override config with command line arguments
        if args.host:
            config.host = args.host
        if args.port:
            config.port = args.port
        if args.prefetch_count:
            config.prefetch_count = args.prefetch_count
        
        config.log_level = args.log_level
        
        # Create and start worker
        worker = FaceWorker(args.worker_id, config=config)
        
        if args.test_mode:
            logger.info("Test mode: initializing worker and exiting...")
            worker.initialize()
            logger.info("Worker initialized successfully in test mode")
            return
        
        # Start the worker (this blocks until shutdown)
        worker.start()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    
    logger.info("Face Recognition Worker Service stopped")


if __name__ == "__main__":
    main()