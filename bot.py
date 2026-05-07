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

# 🔑 Токен з Render / Environment Variables
TOKEN = os.getenv("TOKEN")


# 📊 Наша база продуктів
FOOD_DB = {
    "банан": {"kcal": 89, "protein": 1.1, "fat": 0.3, "carbs": 23},
    "яблуко": {"kcal": 52, "protein": 0.3, "fat": 0.2, "carbs": 14},
    "рис": {"kcal": 130, "protein": 2.7, "fat": 0.3, "carbs": 28},
    "гречка": {"kcal": 110, "protein": 4.5, "fat": 1.6, "carbs": 21},
    "курка": {"kcal": 165, "protein": 31, "fat": 3.6, "carbs": 0},
    "яйце": {"kcal": 155, "protein": 13, "fat": 11, "carbs": 1.1},
    "молоко": {"kcal": 42, "protein": 3.4, "fat": 1, "carbs": 5},
    "хліб": {"kcal": 265, "protein": 9, "fat": 3.2, "carbs": 49},
    "сир": {"kcal": 402, "protein": 25, "fat": 33, "carbs": 1.3},
}


# 🔎 Пошук через Open Food Facts
def get_food_info(product):
    conn = sqlite3.connect("foods.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM foods WHERE name LIKE ?",
        (f"%{product.lower()}%",)
    )

    food = cursor.fetchone()

    conn.close()

   # якщо знайшли у SQLite
if food:
    return f"""
🍽 {food[1].title()}

🔥 Калорії: {food[2]} ккал / 100г
🥩 Білки: {food[3]} г
🧈 Жири: {food[4]} г
🍞 Вуглеводи: {food[5]} г
"""

return "❌ Не знайшла продукт."


# 👋 Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🥗 Привіт! Я бот для підрахунку калорій.\n\nНапиши продукт 🍎"
    )


# 💬 Обробка повідомлень
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    result = get_food_info(text)

    await update.message.reply_text(result)

async def add_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args

        if len(args) != 5:
            await update.message.reply_text(
                "❌ Формат:\n/addfood назва ккал білки жири вуглеводи"
            )
            return

        name = args[0].lower()
        kcal = float(args[1])
        protein = float(args[2])
        fat = float(args[3])
        carbs = float(args[4])

        conn = sqlite3.connect("foods.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO foods (name, kcal, protein, fat, carbs)
            VALUES (?, ?, ?, ?, ?)
        """, (name, kcal, protein, fat, carbs))

        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"✅ Додано: {name}"
        )

    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка: {e}")
# 🚀 Запуск бота
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addfood", add_food))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))


print("✅ Бот запущений...")

app.run_polling(
    poll_interval=3,
    timeout=30,
    drop_pending_updates=True
)