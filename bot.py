import os, random, json
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = "8963926734:AAF1MOvh1SdtfC23C2QhI4iZFjoll4Jpb60"
ADMIN_ID = "1743301387"
TG = f"https://api.telegram.org/bot{BOT_TOKEN}"
JBIN_KEY = "$2a$10$GTPka01SaLPehwlSP01DH.k1WwIyh9Ko2GrTYMN91JAjBL2Dk.EIG"
JBIN_API = "https://api.jsonbin.io/v3/b"
BIN_ID = "6a40d3f1da38895dfe0a9368"

def load_codes():
    try:
        r = requests.get(f"{JBIN_API}/{BIN_ID}/latest",
            headers={"X-Master-Key": JBIN_KEY})
        data = r.json().get("record", {})
        return data.get("codes", {})
    except:
        return {}

def save_codes(codes):
    try:
        requests.put(f"{JBIN_API}/{BIN_ID}", headers={
            "Content-Type": "application/json",
            "X-Master-Key": JBIN_KEY
        }, json={"codes": codes})
    except:
        pass

def make_code():
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    p1 = "".join(random.choices(chars, k=4))
    p2 = "".join(random.choices(chars, k=4))
    return f"TIK-{p1}-{p2}"

def send(chat_id, text):
    requests.post(f"{TG}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    })

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.json
    msg = data.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = msg.get("text", "").strip()
    user_name = msg.get("from", {}).get("first_name", "مجهول")

    if not chat_id or not text:
        return "ok"

    if text == "/generate":
        code = make_code()
        codes = load_codes()
        codes[code] = {"used1": 0, "used2": 0, "cnt1": 0, "cnt2": 0, "owner": chat_id}
        save_codes(codes)

        send(chat_id, (
            f"🎬 <b>TIKRITI — كودك الجديد</b>\n\n"
            f"🔑 <code>{code}</code>\n\n"
            f"✅ يمنحك هذا الكود:\n"
            f"• محاولتين في أداة تحويل FPS\n"
            f"• محاولتين في أداة آيباد\n\n"
            f"📌 انسخ الكود وأدخله في الأداة\n\n"
            f"⚠️ <i>كل كود لشخص واحد فقط</i>"
        ))

        if chat_id != ADMIN_ID:
            send(ADMIN_ID, f"📋 كود جديد صدر\nالكود: <code>{code}</code>\nلـ: {user_name} ({chat_id})")

    elif text == "/start":
        send(chat_id, (
            "👋 أهلاً بك في بوت <b>TIKRITI</b>\n\n"
            "أرسل /generate للحصول على كود الأداة"
        ))

    return "ok"

@app.route("/")
def home():
    return "TIKRITI Bot is running ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
