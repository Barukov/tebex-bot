from flask import Flask, request, jsonify
import requests
import os
import json
from datetime import datetime, timezone

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

DB_FILE = "processed_events.json"


def load_processed():
    if not os.path.exists(DB_FILE):
        return set()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data)
    except Exception:
        return set()


def save_processed(processed):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(list(processed), f, ensure_ascii=False)
    except Exception as e:
        print("Save processed error:", e)


processed_events = load_processed()


def send_telegram(text: str):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Missing TELEGRAM_TOKEN or CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:
        r = requests.post(
            url,
            json={
                "chat_id": CHAT_ID,
                "text": text,
            },
            timeout=10,
        )
        print("Telegram status:", r.status_code, r.text)
    except Exception as e:
        print("Telegram send error:", e)


def parse_dt(created_at: str):
    if created_at:
        try:
            return datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except Exception:
            pass
    return datetime.now(timezone.utc)


@app.get("/")
def home():
    return "OK", 200


@app.post("/webhook")
def webhook():
    try:
        data = request.get_json(silent=True) or {}
        print("Incoming webhook:", data)

        event_type = data.get("type", "")
        event_id = str(data.get("id", "")).strip()
        subject = data.get("subject", {}) or {}

        if event_type == "validation.webhook":
            return jsonify({"id": data.get("id")}), 200

        if event_id and event_id in processed_events:
            print("Duplicate event skipped:", event_id)
            return "ok", 200

        transaction_id = subject.get("transaction_id", "—")

        price = subject.get("price", {}) or {}
        amount = price.get("amount", "—")
        currency = price.get("currency", "")

        customer = subject.get("customer", {}) or {}
        email = customer.get("email", "—")
        first_name = customer.get("first_name", "") or ""
        last_name = customer.get("last_name", "") or ""
        full_name = f"{first_name} {last_name}".strip() or customer.get("username", "—")

        payment_method = subject.get("payment_method", {}) or {}
        method = payment_method.get("name", "—")

        created_at = subject.get("created_at")
        dt = parse_dt(created_at)
        date_str = dt.strftime("%d.%m.%Y")
        time_str = dt.strftime("%H:%M")

        text = None

        if event_type == "payment.completed":
            text = (
                f"✅ Успешная оплата\n\n"
                f"📅 Дата: {date_str}\n"
                f"🕒 Время: {time_str}\n"
                f"💰 Сумма: {amount} {currency}\n"
                f"👤 ФИО: {full_name}\n"
                f"📧 Почта: {email}\n"
                f"💳 Оплата: {method}\n"
                f"🧾 Transaction ID: {transaction_id}"
            )

        elif event_type == "payment.declined":
            reason = subject.get("decline_reason") or "Причина не указана"
            if isinstance(reason, dict):
                reason = reason.get("message", "Причина не указана")

            text = (
                f"❌ Оплата отклонена\n\n"
                f"📅 Дата: {date_str}\n"
                f"🕒 Время: {time_str}\n"
                f"💰 Сумма: {amount} {currency}\n"
                f"👤 ФИО: {full_name}\n"
                f"📧 Почта: {email}\n"
                f"💳 Оплата: {method}\n"
                f"⚠️ Причина: {reason}\n"
                f"🧾 Transaction ID: {transaction_id}"
            )

        elif event_type == "payment.dispute.opened":
            reason = subject.get("reason") or "Причина не указана"
            if isinstance(reason, dict):
                reason = reason.get("message", "Причина не указана")

            text = (
                f"🚨 Чарджбек открыт\n\n"
                f"📅 Дата: {date_str}\n"
                f"🕒 Время: {time_str}\n"
                f"💰 Сумма: {amount} {currency}\n"
                f"👤 ФИО: {full_name}\n"
                f"📧 Почта: {email}\n"
                f"💳 Оплата: {method}\n"
                f"⚠️ Причина: {reason}\n"
                f"🧾 Transaction ID: {transaction_id}"
            )

        elif event_type == "payment.dispute.won":
            text = (
                f"🟢 Чарджбек выигран\n\n"
                f"📅 Дата: {date_str}\n"
                f"🕒 Время: {time_str}\n"
                f"💰 Сумма: {amount} {currency}\n"
                f"👤 ФИО: {full_name}\n"
                f"📧 Почта: {email}\n"
                f"💳 Оплата: {method}\n"
                f"🧾 Transaction ID: {transaction_id}"
            )

        elif event_type == "payment.dispute.lost":
            text = (
                f"🔴 Чарджбек проигран\n\n"
                f"📅 Дата: {date_str}\n"
                f"🕒 Время: {time_str}\n"
                f"💰 Сумма: {amount} {currency}\n"
                f"👤 ФИО: {full_name}\n"
                f"📧 Почта: {email}\n"
                f"💳 Оплата: {method}\n"
                f"🧾 Transaction ID: {transaction_id}"
            )

        elif event_type == "payment.dispute.closed":
            text = (
                f"📁 Чарджбек закрыт\n\n"
                f"📅 Дата: {date_str}\n"
                f"🕒 Время: {time_str}\n"
                f"💰 Сумма: {amount} {currency}\n"
                f"👤 ФИО: {full_name}\n"
                f"📧 Почта: {email}\n"
                f"💳 Оплата: {method}\n"
                f"🧾 Transaction ID: {transaction_id}"
            )

        if text:
            send_telegram(text)

        if event_id:
            processed_events.add(event_id)
            save_processed(processed_events)

        return "ok", 200

    except Exception as e:
        print("Webhook error:", e)
        return "ok", 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
