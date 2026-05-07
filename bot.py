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

# 🔑 TOKEN
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
# 🌍 OPEN FOOD FACTS (по назві)
# =========================
def get_food_by_name(name):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={name}&search_simple=1&action=process&json=1"
    r = requests.get(url).json()

    if not r.get("products"):
        return None

    p = r["products"][0]
    n = p.get("nutriments", {})

    return {
        "name": p.get("product_name", name),
        "kcal": n.get("energy-kcal_100g", 0),
        "protein": n.get("proteins_100g", 0),
        "fat": n.get("fat_100g", 0),
        "carbs": n.get("carbohydrates_100g", 0),
    }


# =========================
# 🔢 OPEN FOOD FACTS (по штрихкоду)
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
# 🧠 DB SEARCH
# =========================
def get_from_db(name):
    conn = sqlite3.connect("foods.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM foods WHERE name LIKE ?",
        (f"%{name.lower()}%",)
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "name": row[1],
            "kcal": row[2],
            "protein": row[3],
            "fat": row[4],
            "carbs": row[5],
        }

    return None


# =========================
# 💾 SAVE
# =========================
def save_to_db(food):
    conn = sqlite3.connect("foods.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO foods (name, kcal, protein, fat, carbs)
        VALUES (?, ?, ?, ?, ?)
    """, (
        food["name"].lower(),
        food["kcal"],
        food["protein"],
        food["fat"],
        food["carbs"],
    ))

    conn.commit()
    conn.close()


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
# 🔍 MAIN SEARCH
# =========================
def get_food(name):
    food = get_from_db(name)
    if food:
        return food

    food = get_food_by_name(name)
    if food:
        save_to_db(food)
        return food

    return None


# =========================
# /START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🥗 Привіт!\n\n"
        "📸 Надішли фото або напиши продукт"
    )


# =========================
# 📸 PHOTO (штрихкод через API)
# =========================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Аналізую штрихкод...")

    # ⚠️ Поки що Telegram не дає barcode напряму
    # 👉 тому тут потрібне майбутнє API (Google Vision / ZXing server)
    # зараз симуляція:

    fake_barcode = "737628064502"  # приклад

    food = get_food_by_barcode(fake_barcode)

    if food:
        await update.message.reply_text(format_food(food))
    else:
        await update.message.reply_text(
            "❌ Продукт не знайдено\n"
            "👉 Напиши вручну:\n"
            "назва ккал білки жири вуглеводи"
        )


# =========================
# 💬 TEXT HANDLER
# =========================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().split()

    # ➕ ДОДАВАННЯ
    if len(text) == 5:
        name, kcal, protein, fat, carbs = text

        save_to_db({
            "name": name,
            "kcal": kcal,
            "protein": protein,
            "fat": fat,
            "carbs": carbs
        })

        await update.message.reply_text("✅ Додано в базу")
        return

    # 🔎 ПОШУК
    food = get_food(text[0])

    if food:
        await update.message.reply_text(format_food(food))
    else:
        await update.message.reply_text("❌ Не знайдено продукт")


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