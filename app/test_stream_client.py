# app/test_stream_client.py
import logging
from typing import Any
from uuid import uuid4
import asyncio

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams,
    SendStreamingMessageRequest,
    SendStreamingMessageSuccessResponse,
)
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    base_url = "http://localhost:10000"

    async with httpx.AsyncClient(timeout=120.0) as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()
        client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

        #user_query = "What is 100 / 4?"  # Начните с простого!
        user_query = "How many seconds would it take for a leopard at full speed to run through Pont des Arts?"
        payload: dict[str, Any] = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": user_query}],
                "message_id": uuid4().hex,
            },
        }

        request = SendStreamingMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**payload)
        )

        logger.info(f"📤 Streaming request: {user_query}")
        print("\n" + "="*50)
        print("STREAMING RESPONSE:")
        print("="*50)

        stream = client.send_message_streaming(request)
        first = True

        async for chunk in stream:
            # Проверяем: есть ли у объекта атрибут 'event'?
            if hasattr(chunk, 'event'):
                # Это событие (status_update, task_completed и т.д.)
                event = chunk.event
                if event == "status_update":
                    status = chunk.payload.status
                    message_text = chunk.payload.message.text if hasattr(chunk.payload, 'message') and chunk.payload.message else ""
                    print(f"🔄 [{status.upper()}] {message_text}")
                elif event == "task_completed":
                    try:
                        final_text = chunk.payload.artifacts[0].parts[0].text
                        print(f"\n✅ FINAL ANSWER: {final_text}")
                    except (KeyError, IndexError, AttributeError):
                        print("❌ Could not extract final answer.")
                elif event == "error":
                    error_msg = chunk.payload.message.text if hasattr(chunk.payload, 'message') and chunk.payload.message else "Unknown error"
                    print(f"❌ ERROR: {error_msg}")
                else:
                    print(f"📦 Other event: {event}")
            else:
                # Первый чанк — SendStreamingMessageSuccessResponse
                if first:
                    print("✅ Task started successfully. Waiting for events...")
                    first = False
                else:
                    print(f"⚠️ Unexpected chunk (no 'event' attr): {type(chunk)}")

        print("="*50)


if __name__ == "__main__":
    asyncio.run(main())