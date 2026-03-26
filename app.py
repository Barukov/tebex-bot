from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime, timezone

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

processed_events = set()

def send_telegram(text: str):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Missing TELEGRAM_TOKEN or CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(
            url,
            json={"chat_id": CHAT_ID, "text": text},
            timeout=10,
        )
    except Exception as e:
        print("Telegram send error:", e)

@app.get("/")
def home():
    return "OK", 200

@app.post("/webhook")
def webhook():
    data = request.get_json(silent=True) or {}

    event_type = data.get("type")
    event_id = str(data.get("id", ""))  # Tebex webhook event id
    subject = data.get("subject", {}) or {}

    # validation webhook
    if event_type == "validation.webhook":
        return jsonify({"id": data.get("id")}), 200

    # защита от дубля
    if event_id and event_id in processed_events:
        print("Duplicate event skipped:", event_id)
        return "ok", 200

    if event_id:
        processed_events.add(event_id)

    price_paid = subject.get("price_paid", {}) or {}
    payment_method = subject.get("payment_method", {}) or {}
    customer = subject.get("customer", {}) or {}

    amount = price_paid.get("amount", "—")
    currency = price_paid.get("currency", "")
    method = payment_method.get("name", "—")

    first_name = customer.get("first_name", "") or ""
    last_name = customer.get("last_name", "") or ""
    full_name = f"{first_name} {last_name}".strip() or customer.get("username", "—")
    email = customer.get("email", "—")

    created_at = subject.get("created_at")
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except Exception:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)

    date_str = dt.strftime("%d.%m.%Y")
    time_str = dt.strftime("%H:%M")

    if event_type == "payment.completed":
        text = (
            f"✅ Успешная оплата\n\n"
            f"📅 Дата: {date_str}\n"
            f"🕒 Время: {time_str}\n"
            f"💰 Сумма: {amount} {currency}\n"
            f"👤 ФИО: {full_name}\n"
            f"📧 Почта: {email}\n"
            f"💳 Оплата: {method}"
        )
        send_telegram(text)

    elif event_type == "payment.declined":
        reason = ((subject.get("decline_reason", {}) or {}).get("message")) or "Причина не указана"
        text = (
            f"❌ Оплата отклонена\n\n"
            f"📅 Дата: {date_str}\n"
            f"🕒 Время: {time_str}\n"
            f"💰 Сумма: {amount} {currency}\n"
            f"👤 ФИО: {full_name}\n"
            f"📧 Почта: {email}\n"
            f"💳 Оплата: {method}\n"
            f"⚠️ Причина: {reason}"
        )
        send_telegram(text)

    return "ok", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "3000"))
    app.run(host="0.0.0.0", port=port)
