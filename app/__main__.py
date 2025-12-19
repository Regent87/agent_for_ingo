# app/__main__.py
import logging
import os
import sys
from dotenv import load_dotenv

import click
import httpx
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from app.agent_executor import MathAgentExecutor

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option('--host', default='localhost')
@click.option('--port', default=10000)
def main(host, port):
    # Проверка API-ключа (опционально)
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY is required")
        sys.exit(1)

    # Описание агента
    capabilities = AgentCapabilities(streaming=True, push_notifications=False)
    skill = AgentSkill(
        id="math_search_agent",
        name="Math & Search Agent",
        description="Solves real-world math problems by searching for facts and performing calculations.",
        tags=["math", "search", "calculation"],
        examples=[
            "How many seconds would it take for a leopard at full speed to run through Pont des Arts?",
            "What is the area of a circle with radius 5 meters?"
        ],
    )
    agent_card = AgentCard(
        name="Math & Search Agent",
        description="Searches the web for real-world data and computes answers.",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=capabilities,
        skills=[skill],
    )

    # Инициализация A2A-сервера
    httpx_client = httpx.AsyncClient()
    push_config_store = InMemoryPushNotificationConfigStore()
    push_sender = BasePushNotificationSender(httpx_client=httpx_client, config_store=push_config_store)
    request_handler = DefaultRequestHandler(
        agent_executor=MathAgentExecutor(),
        task_store=InMemoryTaskStore(),
        push_config_store=push_config_store,
        push_sender=push_sender,
    )
    server = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)

    uvicorn.run(server.build(), host=host, port=port)

if __name__ == "__main__":
    main()