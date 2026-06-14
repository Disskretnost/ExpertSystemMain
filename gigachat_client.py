import os
from dotenv import load_dotenv
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

load_dotenv()

giga = GigaChat(
    credentials=os.getenv("GIGACHAT_CREDENTIALS"),
    verify_ssl_certs=False,
    model="GigaChat:latest"
)


def get_gigachat_response(prompt: str) -> str:
    try:
        response = giga.chat(Chat(messages=[
            Messages(role=MessagesRole.USER, content=prompt)
        ]))
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Ошибка GigaChat: {str(e)}")


if __name__ == "__main__":
    test_prompt = "Привет! Напиши одно предложение о здоровье сердца."
    result = get_gigachat_response(test_prompt)
    print("Тест GigaChat клиента:")
    print("=" * 50)
    print(result)
    print("=" * 50)
    print("✅ Клиент работает!")