# chat_ui.py
import streamlit as st
from dotenv import load_dotenv
import os
import asyncio
from app.agent import MathAgent

# Загружаем переменные окружения
load_dotenv()

# Проверка API-ключа
if not os.getenv("OPENAI_API_KEY"):
    st.error("❌ OPENAI_API_KEY не найден. Убедитесь, что он есть в файле `.env` в корне проекта.")
    st.stop()

# Настройка страницы
st.set_page_config(
    page_title="Math & Search Agent",
    page_icon="🧠",
    layout="centered"
)

st.title("🧠 Простой агент для поиска и математических подсчетов")
st.caption("Задавай вопросы типа: _'Сколько понадобится времени гепарду, чтобы пересечь Москву-реку по Большому Каменному мосту ?'_")

# Инициализация агента (один раз на сессию)
@st.cache_resource
def get_agent():
    return MathAgent()

agent = get_agent()

# Инициализация состояния чата и контекста
if "messages" not in st.session_state:
    st.session_state.messages = []
if "context_id" not in st.session_state:
    # Генерируем уникальный ID для сессии
    st.session_state.context_id = f"streamlit_session_{id(st.session_state)}"

# Отображение истории чата
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Обработка нового сообщения
if prompt := st.chat_input("Задай свой вопрос..."):
    # Добавляем сообщение пользователя
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Ответ агента
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        context_id = st.session_state.context_id  # ← ОДИН КОНТЕКСТ НА ВСЮ СЕССИЮ

        try:
            async def get_response():
                async for chunk in agent.stream(prompt, context_id):
                    if not chunk["is_task_complete"]:
                        # Промежуточный статус
                        message_placeholder.markdown(f"⏳ {chunk['content']}")
                    else:
                        # Финальный ответ
                        return chunk["content"]
                return "No response generated."

            # Запускаем асинхронную функцию
            final_answer = asyncio.run(get_response())
            message_placeholder.markdown(final_answer)
            st.session_state.messages.append({"role": "assistant", "content": final_answer})

        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            message_placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})