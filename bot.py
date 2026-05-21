import os
import json
import sqlite3
import requests

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from google.cloud import vision
from google.oauth2 import service_account


# =========================
# 🔑 ENV
# =========================
TOKEN = os.getenv("TOKEN")

from google.cloud import vision
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    "credentials.json"
)

client = vision.ImageAnnotatorClient(credentials=credentials)


# =========================
# 🗄 DB
# =========================
def init_db():
    conn = sqlite3.connect("foods.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            kcal REAL,
            protein REAL,
            fat REAL,
            carbs REAL
        )
    """)

    conn.commit()
    conn.close()


# =========================
# 🍽 LOCAL DB SEARCH
# =========================
def get_from_db(name):
    conn = sqlite3.connect("foods.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM foods WHERE name LIKE ?", (f"%{name.lower()}%",))
    food = cursor.fetchone()

    conn.close()

    if food:
        return {
            "name": food[1],
            "kcal": food[2],
            "protein": food[3],
            "fat": food[4],
            "carbs": food[5],
        }
    return None


# =========================
# 🌍 OPEN FOOD FACTS
# =========================
def get_food_by_barcode(barcode):
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    r = requests.get(url).json()

    if r.get("status") != 1:
        return None

    p = r["product"]
    n = p.get("nutriments", {})

    return {
        "name": p.get("product_name", "unknown"),
        "kcal": n.get("energy-kcal_100g", 0),
        "protein": n.get("proteins_100g", 0),
        "fat": n.get("fat_100g", 0),
        "carbs": n.get("carbohydrates_100g", 0),
    }


# =========================
# 📸 GOOGLE VISION BARCODE
# =========================
def decode_barcode_google(image_bytes):
    image = vision.Image(content=image_bytes)

    response = client.text_detection(image=image)

    texts = response.text_annotations

    if not texts:
        return None

    raw = texts[0].description

    barcode = "".join(filter(str.isdigit, raw))

    if len(barcode) < 8:
        return None

    return barcode


# =========================
# 🍽 FORMAT
# =========================
def format_food(food):
    return f"""
🍽 {food['name']}

🔥 Калорії: {food['kcal']}
🥩 Білки: {food['protein']}
🧈 Жири: {food['fat']}
🍞 Вуглеводи: {food['carbs']}
"""


# =========================
# 👋 START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🥗 Бот КБЖВ запущений\n\n"
        "📸 Надішли фото штрихкоду\n"
        "✍️ або напиши продукт"
    )


# =========================
# 📸 PHOTO HANDLER
# =========================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Розпізнаю штрихкод...")

    photo = update.message.photo[-1]
    file = await photo.get_file()
    image = await file.download_as_bytearray()

    barcode = decode_barcode_google(image)

    if not barcode:
        await update.message.reply_text("❌ Не вдалося розпізнати штрихкод")
        return

    food = get_food_by_barcode(barcode)

    if food:
        await update.message.reply_text(format_food(food))
    else:
        await update.message.reply_text(
            f"❌ Не знайдено продукт (barcode: {barcode})\n"
            "👉 Додай вручну:\n"
            "назва ккал білки жири вуглеводи"
        )


# =========================
# 💬 TEXT HANDLER
# =========================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().split()

    # ➕ ADD FOOD
    if len(text) == 5:
        name, kcal, protein, fat, carbs = text

        conn = sqlite3.connect("foods.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO foods (name, kcal, protein, fat, carbs)
            VALUES (?, ?, ?, ?, ?)
        """, (name, kcal, protein, fat, carbs))

        conn.commit()
        conn.close()

        await update.message.reply_text("✅ Додано в базу")
        return

    # 🔎 SEARCH
    food = get_from_db(text[0])

    if food:
        await update.message.reply_text(format_food(food))
    else:
        await update.message.reply_text("❌ Не знайдено. Спробуй фото або додай вручну")


# =========================
# 🚀 RUN
# =========================
def main():
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🚀 Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()