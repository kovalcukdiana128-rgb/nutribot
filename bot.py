import os
import requests
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
def get_food_api(product):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={product}&search_simple=1&action=process&json=1"

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        products = data.get("products", [])

        if not products:
            return None

        item = products[0]
        nutriments = item.get("nutriments", {})

        return f"""
🍽 {item.get('product_name', 'Unknown')}

🔥 Калорії: {nutriments.get('energy-kcal_100g', 0)} ккал / 100г
🥩 Білки: {nutriments.get('proteins_100g', 0)} г
🧈 Жири: {nutriments.get('fat_100g', 0)} г
🍞 Вуглеводи: {nutriments.get('carbohydrates_100g', 0)} г
"""

    except:
        return None


# 🧠 Головна функція
def get_food_info(product):
    product = product.lower()

    # 🔥 Спочатку шукаємо у своїй базі
    if product in FOOD_DB:
        food = FOOD_DB[product]

        return f"""
🍽 {product.title()}

🔥 Калорії: {food['kcal']} ккал / 100г
🥩 Білки: {food['protein']} г
🧈 Жири: {food['fat']} г
🍞 Вуглеводи: {food['carbs']} г
"""

    # 🌍 Якщо нема — шукаємо через API
    api_result = get_food_api(product)

    if api_result:
        return api_result

    return "❌ Не знайшла продукт. Спробуй іншу назву."


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


# 🚀 Запуск бота
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("✅ Бот запущений...")

app.run_polling()