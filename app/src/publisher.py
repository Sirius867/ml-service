import os

import pika

from .exceptions import BrokerError
from .messages import MLTaskMessage


class RabbitPublisher:
    def __init__(self) -> None:
        self._queue_name = os.getenv("RABBITMQ_QUEUE", "ml_tasks")

    def publish(self, message: MLTaskMessage) -> None:
        try:
            connection = pika.BlockingConnection(_connection_parameters())
            try:
                channel = connection.channel()
                channel.queue_declare(queue=self._queue_name, durable=True)
                channel.confirm_delivery()
                published = channel.basic_publish(
                    exchange="",
                    routing_key=self._queue_name,
                    body=message.model_dump_json(),
                    properties=pika.BasicProperties(
                        content_type="application/json",
                        delivery_mode=2,
                    ),
                    mandatory=True,
                )
                if not published:
                    raise BrokerError("RabbitMQ не подтвердил публикацию задачи")
            finally:
                connection.close()
        except BrokerError:
            raise
        except pika.exceptions.AMQPError as exc:
            raise BrokerError("Не удалось отправить задачу в RabbitMQ") from exc


def _connection_parameters() -> pika.ConnectionParameters | pika.URLParameters:
    if url := os.getenv("RABBITMQ_URL"):
        return pika.URLParameters(url)

    credentials = pika.PlainCredentials(
        os.getenv("RABBITMQ_USER", "guest"),
        os.getenv("RABBITMQ_PASSWORD", "guest"),
    )
    return pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        credentials=credentials,
        heartbeat=60,
        blocked_connection_timeout=30,
    )
