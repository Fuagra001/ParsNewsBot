import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def parse_channel(url: str, days: int = 30) -> tuple[list[str], str, str]:
    """
    Парсит канал из браузерной версии Telegram и возвращает:
    - список сообщений за последние N дней,
    - дату самого старого сообщения,
    - дату самого нового сообщения
    """
    if "/s/" not in url:
        url = url.replace("t.me/", "t.me/s/")

    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    posts = soup.find_all("div", class_="tgme_widget_message")

    since = datetime.now(timezone.utc) - timedelta(days=days)
    messages = []
    first_date = None
    last_date = None

    for post in posts:
        time_tag = post.find("time")
        if not time_tag or "datetime" not in time_tag.attrs:
            continue

        post_date = datetime.fromisoformat(time_tag["datetime"])
        if post_date.tzinfo is None:
            post_date = post_date.replace(tzinfo=timezone.utc)

        if post_date < since:
            continue

        text_tag = post.find("div", class_="tgme_widget_message_text")
        if text_tag:
            messages.append(text_tag.get_text(" ", strip=True))
            if not first_date or post_date < first_date:
                first_date = post_date
            if not last_date or post_date > last_date:
                last_date = post_date

    first_str = first_date.strftime("%Y-%m-%d") if first_date else "N/A"
    last_str = last_date.strftime("%Y-%m-%d") if last_date else "N/A"

    return messages, first_str, last_str
