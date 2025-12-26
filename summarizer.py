from openai import OpenAI

client = OpenAI(api_key="AI_TOKEN")

def make_summary(channel_url: str, messages: list[str], period: tuple[str, str], max_chars: int = 3000) -> str:
    """
    Создаёт ИИ-конспект по последним сообщениям.
    period: кортеж (start_date, end_date)
    """
    text = "\n".join(messages)
    if len(text) > max_chars:
        text = text[-max_chars:]  # берём последние символы

    start_date, end_date = period

    prompt = f"""
Сделай очеь подробный КОНСПЕКТ Telegram-канала за период с {start_date} по {end_date}.

Формат:
1. Основные темы
2. Ключевые события
3. Краткие выводы

Сообщения:
{text}
"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return f"📌 Отчёт по каналу {channel_url}\nПериод сообщений: {start_date} — {end_date}\n\n{resp.choices[0].message.content}"

