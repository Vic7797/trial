import aio_pika
from aio_pika.abc import AbstractRobustConnection
from aio_pika.pool import Pool
from typing import Optional, Callable, Any
import asyncio
import json
from functools import partial
import logging
from datetime import datetime
from aio_pika import ExchangeType, Message
from app.config import settings

from app.config import settings

# Connection pool settings
POOL_SIZE = 2

logger = logging.getLogger(__name__)

# Queue names
TICKET_QUEUE = "tickets"
NOTIFICATION_QUEUE = "notifications"
EMAIL_QUEUE = "emails"
TELEGRAM_QUEUE = "telegram"

# Dead Letter Exchange and Queue names
DLX_NAME = "dlx"
DLQ_NAME = "dead_letter_queue"


async def get_connection() -> AbstractRobustConnection:
    """Create a new RabbitMQ connection."""
    return await aio_pika.connect_robust(
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
        login=settings.RABBITMQ_USER,
        password=settings.RABBITMQ_PASSWORD,
        virtualhost=settings.RABBITMQ_VHOST,
        timeout=settings.RABBITMQ_CONNECTION_TIMEOUT,
        heartbeat=settings.RABBITMQ_HEARTBEAT
    )


# Connection pool
connection_pool: Optional[Pool] = None


async def init_rabbitmq_pool():
    """Initialize the RabbitMQ connection pool."""
    global connection_pool
    connection_pool = Pool(get_connection, max_size=POOL_SIZE)


async def get_rabbitmq_channel():
    """Get a channel from the connection pool."""
    if connection_pool is None:
        await init_rabbitmq_pool()
    
    async with connection_pool.acquire() as connection:
        return await connection.channel()


class MessageQueue:
    """RabbitMQ message queue implementation."""

    @staticmethod
    async def setup_dead_letter_queue(channel):
        """Setup dead letter exchange and queue."""
        # Declare the dead letter exchange
        dlx = await channel.declare_exchange(
            DLX_NAME,
            ExchangeType.DIRECT,
            durable=True
        )

        # Declare the dead letter queue
        dlq = await channel.declare_queue(
            DLQ_NAME,
            durable=True,
            arguments={
                'x-message-ttl': 1000 * 60 * 60 * 24 * 7,  # 7 days TTL
                'x-max-length': 10000
            }
        )
        await dlq.bind(dlx)
        return dlx

    @staticmethod
    async def declare_queue(
        queue_name: str,
        durable: bool = True,
        auto_delete: bool = False
    ):
        """Declare a queue with dead letter exchange configuration."""
        async with await get_rabbitmq_channel() as channel:
            # Create dead letter exchange if not exists
            dlx = await MessageQueue.setup_dead_letter_queue(channel)
            
            # Declare the main queue with DLX configuration
            queue = await channel.declare_queue(
                queue_name,
                durable=durable,
                auto_delete=auto_delete,
                arguments={
                    'x-dead-letter-exchange': DLX_NAME,
                    'x-message-ttl': 1000 * 60 * 60 * 24,  # 24h TTL
                    'x-max-priority': 10
                }
            )
            return queue

    @staticmethod
    async def publish(
        queue_name: str,
        message: dict,
        routing_key: str = "",
        retry_count: int = 3,
        priority: int = 0,
        expiration: int = None
    ):
        """Publish a message to a queue."""
        try:
            async with await get_rabbitmq_channel() as channel:
                # Ensure queue exists
                queue = await MessageQueue.declare_queue(queue_name)
                
                # Add metadata
                message.update({
                    'timestamp': datetime.utcnow().isoformat(),
                    'retry_count': retry_count
                })
                
                # Create message with properties
                message_body = Message(
                    body=json.dumps(message).encode(),
                    content_type='application/json',
                    content_encoding='utf-8',
                    priority=priority,
                    expiration=str(expiration) if expiration else None,
                    headers={'retry_count': retry_count}
                )
                
                # Publish message
                await channel.default_exchange.publish(
                    message_body,
                    routing_key=queue.name
                )
                
                logger.info(f"Published message to queue {queue_name}")
                
        except Exception as e:
            logger.error(f"Error publishing message: {str(e)}")
            raise

    @staticmethod
    async def move_to_dlq(
        channel,
        message: aio_pika.IncomingMessage,
        reason: str
    ):
        """Move a message to the dead letter queue."""
        try:
            headers = message.headers or {}
            headers.update({
                'x-death-reason': reason,
                'x-death-time': datetime.utcnow().isoformat()
            })
            
            # Create new message for DLQ
            dlq_message = Message(
                body=message.body,
                headers=headers,
                content_type=message.content_type,
                content_encoding=message.content_encoding,
                delivery_mode=message.delivery_mode
            )
            
            # Get DLX and publish
            dlx = await channel.declare_exchange(
                DLX_NAME,
                ExchangeType.DIRECT,
                durable=True
            )
            await dlx.publish(dlq_message, routing_key=DLQ_NAME)
            
            logger.info(f"Moved message to DLQ: {reason}")
            
        except Exception as e:
            logger.error(f"Error moving message to DLQ: {str(e)}")
            raise

    @staticmethod
    async def retry_failed_message(message: aio_pika.IncomingMessage):
        """Retry a failed message with exponential backoff."""
        try:
            retry_count = message.headers.get('retry_count', 0)
            if retry_count >= 3:  # Max retries
                async with await get_rabbitmq_channel() as channel:
                    await MessageQueue.move_to_dlq(
                        channel,
                        message,
                        "max_retries_exceeded"
                    )
                return

            # Increment retry count
            message.headers['retry_count'] = retry_count + 1
            
            # Calculate delay with exponential backoff
            delay = (2 ** retry_count) * 1000  # milliseconds
            
            # Republish with delay
            async with await get_rabbitmq_channel() as channel:
                await message.retry(
                    channel,
                    delay=delay,
                    headers=message.headers
                )
                
            logger.info(
                f"Retrying message, attempt {retry_count + 1}, "
                f"delay {delay}ms"
            )
            
        except Exception as e:
            logger.error(f"Error retrying message: {str(e)}")
            raise

    @staticmethod
    async def consume(
        queue_name: str,
        callback: Callable[[dict], Any],
        prefetch_count: int = 10
    ):
        """Consume messages from a queue."""
        try:
            async with await get_rabbitmq_channel() as channel:
                # Set QoS
                await channel.set_qos(prefetch_count=prefetch_count)
                
                # Ensure queue exists
                queue = await MessageQueue.declare_queue(queue_name)
                
                # Start consuming
                async with queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        try:
                            async with message.process():
                                # Parse message
                                body = json.loads(message.body.decode())
                                
                                # Process message
                                await callback(body)
                                
                        except Exception as e:
                            logger.error(
                                f"Error processing message: {str(e)}",
                                exc_info=True
                            )
                            await MessageQueue.retry_failed_message(message)
                            
        except Exception as e:
            logger.error(f"Error in consumer: {str(e)}")
            raise


async def process_dead_letter_queue(retry_interval: int = 3600):
    """Process messages in the dead letter queue periodically."""
    while True:
        try:
            async with await get_rabbitmq_channel() as channel:
                queue = await channel.declare_queue(
                    DLQ_NAME,
                    durable=True
                )
                
                # Process each message in DLQ
                async with queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        async with message.process():
                            # Log failed message
                            body = json.loads(message.body.decode())
                            headers = message.headers or {}
                            
                            logger.error(
                                "Dead letter message",
                                extra={
                                    'message': body,
                                    'headers': headers,
                                    'death_reason': headers.get('x-death-reason'),
                                    'death_time': headers.get('x-death-time')
                                }
                            )
                            
            # Wait before next processing
            await asyncio.sleep(retry_interval)
            
        except Exception as e:
            logger.error(f"Error processing DLQ: {str(e)}")
            await asyncio.sleep(60)  # Wait before retry
