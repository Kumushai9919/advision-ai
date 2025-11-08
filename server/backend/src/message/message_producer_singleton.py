from src.message.message_producer import MessageProducer, ProducerConfig
from src.core.logger import logger

class MessageProducerSingleton:
    _instance = None
    _producer = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_producer(self) -> MessageProducer:
        """
            Get or create the message producer instance.
        """
        if self._producer is None or not self._is_healthy():
            try:
                if self._producer:
                    self._producer.close()
            except:
                logger.warning("Failed to close existing producer, proceeding to create a new one.")
            
            self._producer = MessageProducer()
            logger.info("MessageProducer instance created.")
        
        return self._producer

    def _is_healthy(self) -> bool:
        """Check if the producer connection is healthy"""
        if not self._producer:
            return False
        
        try:
            if self._producer.connection and not self._producer.connection.is_closed:
                return True
        except:
            pass
        
        return False
    
    def close(self):
        """Close the producer connection"""
        if self._producer:
            try:
                self._producer.close()
                logger.info("Message producer closed")
            except Exception as e:
                logger.error(f"Error closing message producer: {e}")
            finally:
                self._producer = None
                
message_producer_singleton = MessageProducerSingleton()