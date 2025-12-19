# app/test_client.py
import logging
from typing import Any
from uuid import uuid4
import asyncio

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    EXTENDED_AGENT_CARD_PATH,
)


async def main() -> None:
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    base_url = "http://localhost:10000"

    async with httpx.AsyncClient(timeout=60.0) as httpx_client:
        # === 1. Получение Agent Card ===
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        logger.info(f"Fetching agent card from: {base_url}{AGENT_CARD_WELL_KNOWN_PATH}")

        try:
            public_card = await resolver.get_agent_card()
            logger.info("✅ Public agent card fetched:")
            logger.info(public_card.model_dump_json(indent=2, exclude_none=True))
            final_agent_card = public_card
        except Exception as e:
            logger.error(f"❌ Failed to fetch agent card: {e}")
            raise

        # === 2. Инициализация клиента ===
        client = A2AClient(httpx_client=httpx_client, agent_card=final_agent_card)
        logger.info("✅ A2AClient initialized.")

        # === 3. Тестовый запрос: ваш вопрос ===
        user_query = "Сколько понадобится времени гепарду, чтобы пересечь Москву-реку по Большому Каменному мосту ?"
        #user_query = "What is 100 / 4?"

        send_message_payload: dict[str, Any] = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": user_query}],
                "message_id": uuid4().hex,
            },
        }

        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**send_message_payload)
        )

        logger.info(f"📤 Sending request: {user_query}")
        response = await client.send_message(request)

        logger.info("✅ Received response:")
        result = response.model_dump(mode="json", exclude_none=True)
        print("\n" + "="*60)
        print("FINAL ANSWER:")
        # Извлекаем текст из artifacts
        try:
            text = result["result"]["artifacts"][0]["parts"][0]["text"]
            print(text)
        except (KeyError, IndexError):
            print("❌ Could not extract answer from response:")
            print(result)
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())