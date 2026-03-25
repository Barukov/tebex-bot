# Tebex -> Telegram webhook for Render

## Что делает
Отправляет в Telegram только два статуса:
- `payment.completed`
- `payment.declined`

## Файлы
- `app.py` — Flask webhook
- `requirements.txt`
- `render.yaml` — автоконфиг для Render

## Как запустить на Render
1. Создай новый GitHub репозиторий и загрузи туда эти 3 файла.
2. На Render выбери **New Web Service** и подключи этот репозиторий.
3. Добавь env:
   - `TELEGRAM_TOKEN`
   - `CHAT_ID`
4. Deploy.
5. Возьми URL:
   `https://your-service.onrender.com/webhook`
6. В Tebex создай endpoint и выбери события:
   - `payment.completed`
   - `payment.declined`

## Формат сообщений
Успех и отклонение с датой, временем, суммой, ФИО, почтой и способом оплаты.
