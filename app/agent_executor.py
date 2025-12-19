# app/agent_executor.py
import asyncio
import logging
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Part,
    TaskState,
    TextPart,
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError
from app.agent import MathAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MathAgentExecutor(AgentExecutor):
    def __init__(self):
        self.agent = MathAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        query = context.get_user_input()
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)
        try:
            async for item in self.agent.stream(query, task.context_id):
                if item["is_task_complete"]:
                    await updater.add_artifact(
                        [Part(root=TextPart(text=item["content"]))],
                        name="calculation_result",
                    )
                    await updater.complete()
                    break
                else:
                    # Отправляем промежуточный статус
                    message = new_agent_text_message(
                        item["content"],
                        task.context_id,
                        task.id,
                    )
                    await updater.update_status(TaskState.working, message)
                    
                    # 🔥 Даём клиенту время подключиться к streaming
                    await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in MathAgentExecutor: {e}")
            raise ServerError(error=InternalError()) from e

    def _validate_request(self, context: RequestContext) -> bool:
        return False

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass