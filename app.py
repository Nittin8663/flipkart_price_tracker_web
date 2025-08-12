import threading
import time
from flask import Flask, request, render_template, redirect, url_for, flash
import requests as pyrequests
from bs4 import BeautifulSoup
import telegram

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Product format: {'url': ..., 'target_price': ..., 'last_price': ...}
products = []  # In-memory database

# Telegram settings
TELEGRAM_TOKEN = ''
TELEGRAM_CHAT_ID = ''

def get_flipkart_price(url):
    headers = {
        "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    try:
        r = pyrequests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.content, "html.parser")
        price_tags = soup.find_all('div', {'class': '_30jeq3 _16Jk6d'})
        if not price_tags:
            price_tags = soup.find_all('div', {'class': '_30jeq3'})
        if price_tags:
            price_text = price_tags[0].text.replace('₹', '').replace(',', '').strip()
            return int(price_text)
    except Exception as e:
        print(f"Error fetching price: {e}")
    return None

def send_telegram(message):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            bot = telegram.Bot(token=TELEGRAM_TOKEN)
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        except Exception as e:
            print(f"Telegram Error: {e}")

def price_tracker():
    while True:
        for product in products:
            price = get_flipkart_price(product['url'])
            if price is not None:
                if product.get('last_price') != price:
                    product['last_price'] = price
                if price <= product['target_price']:
                    msg = f"Price drop!\n{product['url']}\nCurrent: ₹{price}, Target: ₹{product['target_price']}"
                    send_telegram(msg)
        time.sleep(60)

@app.route("/", methods=["GET", "POST"])
def index():
    global TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
    if request.method == "POST":
        if 'add_product' in request.form:
            url = request.form.get("url", "").strip()
            target_price = request.form.get("target_price", "").strip()
            try:
                target_price = int(target_price)
                products.append({'url': url, 'target_price': target_price, 'last_price': None})
                flash("Product added!", "success")
            except:
                flash("Target price must be a number.", "danger")
        elif 'set_telegram' in request.form:
            TELEGRAM_TOKEN = request.form.get("telegram_token", "").strip()
            TELEGRAM_CHAT_ID = request.form.get("telegram_chat_id", "").strip()
            flash("Telegram settings updated.", "success")
        elif 'delete' in request.form:
            idx = int(request.form.get("delete"))
            products.pop(idx)
            flash("Product deleted.", "success")
        return redirect(url_for('index'))
    return render_template("index.html", products=products, telegram_token=TELEGRAM_TOKEN, telegram_chat_id=TELEGRAM_CHAT_ID)

if __name__ == "__main__":
    # Start background tracker
    thread = threading.Thread(target=price_tracker, daemon=True)
    thread.start()
    app.run(host="0.0.0.0", port=5000)
