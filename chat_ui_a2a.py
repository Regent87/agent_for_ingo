# chat_ui_a2a.py
import streamlit as st
import httpx
from uuid import uuid4
from a2a.types import MessageSendParams, SendMessageRequest
import os

# URL вашего A2A-агента
#A2A_AGENT_URL = "http://localhost:10000"
A2A_AGENT_URL = os.getenv("A2A_AGENT_URL", "http://localhost:10000")

st.set_page_config(page_title="A2A Agent Chat", page_icon="🔌", layout="centered")
st.title("🔌 A2A Agent Chat (with memory)")
st.caption("Talk to your A2A agent running on http://localhost:10000")

# Инициализация состояния
if "messages" not in st.session_state:
    st.session_state.messages = []
if "a2a_context_id" not in st.session_state:
    st.session_state.a2a_context_id = None

# Отображение истории чата
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Обработка нового сообщения
if prompt := st.chat_input("Type your message..."):
    # Добавляем сообщение пользователя
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Ответ агента
    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        msg_placeholder.markdown("⏳ Thinking...")

        try:
            # === Формируем сообщение ===
            message_data = {
                "role": "user",
                "parts": [{"kind": "text", "text": prompt}],
                "message_id": uuid4().hex,
            }

            # 🔥 ПЕРЕДАЁМ context_id, если он есть (для продолжения диалога)
            if st.session_state.a2a_context_id:
                message_data["context_id"] = st.session_state.a2a_context_id

            # Создаём запрос точно как в test_client.py
            send_message_payload = {"message": message_data}
            request = SendMessageRequest(
                id=str(uuid4()),
                params=MessageSendParams(**send_message_payload)
            )

            # Отправляем запрос на корень с правильным заголовком
            response = httpx.post(
                A2A_AGENT_URL,
                json=request.model_dump(mode="json"),
                headers={"Content-Type": "application/json"},
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()

            # Отладка (можно удалить)
            print("Sending context_id:", message_data.get("context_id"))
            print("RAW RESPONSE TEXT:", response.text)

            # === Обрабатываем ответ ===
            try:
                result = data["result"]

                # 🔥 СОХРАНЯЕМ contextId для последующих запросов
                st.session_state.a2a_context_id = result.get("contextId")

                # Извлекаем текст из artifacts
                artifacts = result.get("artifacts", [])
                if (artifacts and 
                    isinstance(artifacts[0].get("parts"), list) and 
                    len(artifacts[0]["parts"]) > 0):
                    answer_text = artifacts[0]["parts"][0].get("text", "No text in response.")
                else:
                    answer_text = "❌ No valid 'artifacts' in response."

                msg_placeholder.markdown(answer_text)
                st.session_state.messages.append({"role": "assistant", "content": answer_text})

            except (KeyError, IndexError, TypeError, AttributeError) as e:
                error_detail = f"Failed to parse response: {str(e)}"
                msg_placeholder.markdown(f"❌ {error_detail}")
                st.session_state.messages.append({"role": "assistant", "content": f"❌ {error_detail}"})

        except Exception as e:
            error_msg = f"❌ Request failed: {str(e)}"
            msg_placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})