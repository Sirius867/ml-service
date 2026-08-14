import logging
import os
import time

import pika
from pydantic import ValidationError

from .database import SessionFactory
from .exceptions import ServiceError
from .messages import MLTaskMessage, MLTaskResult
from .publisher import _connection_parameters
from .services import MLService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def run_worker() -> None:
    worker_id = os.getenv("WORKER_ID", "worker")
    queue_name = os.getenv("RABBITMQ_QUEUE", "ml_tasks")
    service = MLService(SessionFactory)

    while True:
        try:
            connection = pika.BlockingConnection(_connection_parameters())
            channel = connection.channel()
            channel.queue_declare(queue=queue_name, durable=True)
            channel.basic_qos(prefetch_count=1)

            def handle_message(
                _: pika.adapters.blocking_connection.BlockingChannel,
                method: pika.spec.Basic.Deliver,
                __: pika.BasicProperties,
                body: bytes,
            ) -> None:
                try:
                    message = MLTaskMessage.model_validate_json(body)
                except ValidationError as exc:
                    logger.error("Некорректное сообщение: %s", exc)
                    channel.basic_ack(delivery_tag=method.delivery_tag)
                    return

                try:
                    task = service.process_prediction_task(
                        message.task_id,
                        message.model,
                        message.features,
                    )
                    result = MLTaskResult(
                        task_id=task.id,
                        prediction=task.prediction,
                        worker_id=worker_id,
                        status="success" if task.status == "completed" else task.status,
                    )
                    logger.info("%s", result.model_dump_json())
                    channel.basic_ack(delivery_tag=method.delivery_tag)
                except ServiceError:
                    logger.exception("Задача %s отклонена", message.task_id)
                    channel.basic_ack(delivery_tag=method.delivery_tag)
                except Exception:
                    logger.exception("Ошибка обработки задачи %s", message.task_id)
                    channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

            channel.basic_consume(queue=queue_name, on_message_callback=handle_message)
            logger.info("%s ожидает задачи из очереди %s", worker_id, queue_name)
            channel.start_consuming()
        except pika.exceptions.AMQPError:
            logger.exception("Соединение с RabbitMQ потеряно")
            time.sleep(5)


if __name__ == "__main__":
    run_worker()
