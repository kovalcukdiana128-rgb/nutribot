import os
import requests
import sqlite3

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TOKEN")


# =========================
# 🗄 DATABASE
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
# 📸 REAL BARCODE FROM IMAGE
# =========================
async def decode_barcode(image_bytes):
    """
    🔥 Реальне розпізнавання через хмарний API
    """

    try:
        url = "https://api.zxing.org/decode"

        files = {"file": ("image.jpg", image_bytes)}

        response = requests.post(url, files=files, timeout=20)

        data = response.json()

        if not data.get("success"):
            return None

        return data["data"][0]["rawValue"]

    except:
        return None


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
# 📸 PHOTO HANDLER
# =========================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Сканую штрихкод...")

    photo = update.message.photo[-1]
    file = await photo.get_file()
    image = await file.download_as_bytearray()

    barcode = await decode_barcode(image)

    if not barcode:
        await update.message.reply_text(
            "❌ Не вдалося розпізнати штрихкод\n"
            "👉 Спробуй ще раз або введи назву вручну"
        )
        return

    food = get_food_by_barcode(barcode)

    if food:
        await update.message.reply_text(format_food(food))
    else:
        await update.message.reply_text(
            f"❌ Продукт не знайдено (barcode: {barcode})\n"
            "👉 Хочеш додати в базу? Напиши:\n"
            "назва ккал білки жири вуглеводи"
        )


# =========================
# 💬 TEXT HANDLER
# =========================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().split()

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

    await update.message.reply_text("📸 Надішли фото штрихкоду або введи продукт")


# =========================
# 🚀 START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🥗 Бот КБЖВ готовий\n\n"
        "📸 Надішли фото штрихкоду\n"
        "✍️ або напиши продукт"
    )


# =========================
# RUN
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