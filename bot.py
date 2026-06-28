import os, random, json
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = "8963926734:AAF1MOvh1SdtfC23C2QhI4iZFjoll4Jpb60"
ADMIN_ID = "1743301387"
CHANNEL = "@tikriti99"  # اسم قناتك
TG = f"https://api.telegram.org/bot{BOT_TOKEN}"
JBIN_KEY = "$2a$10$GTPka01SaLPehwlSP01DH.k1WwIyh9Ko2GrTYMN91JAjBL2Dk.EIG"
JBIN_API = "https://api.jsonbin.io/v3/b"
BIN_ID = "6a40d3f1da38895dfe0a9368"

# ── قاعدة البيانات ──────────────────────────────────────────────
def load_db():
    try:
        r = requests.get(f"{JBIN_API}/{BIN_ID}/latest",
            headers={"X-Master-Key": JBIN_KEY})
        return r.json().get("record", {"codes": {}, "users": {}})
    except:
        return {"codes": {}, "users": {}}

def save_db(db):
    try:
        requests.put(f"{JBIN_API}/{BIN_ID}", headers={
            "Content-Type": "application/json",
            "X-Master-Key": JBIN_KEY
        }, json=db)
    except:
        pass

# ── مساعدات ─────────────────────────────────────────────────────
def make_code():
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    p1 = "".join(random.choices(chars, k=4))
    p2 = "".join(random.choices(chars, k=4))
    return f"TIK-{p1}-{p2}"

def send(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if keyboard:
        payload["reply_markup"] = {"inline_keyboard": keyboard}
    requests.post(f"{TG}/sendMessage", json=payload)

def is_subscribed(chat_id):
    try:
        r = requests.get(f"{TG}/getChatMember", params={
            "chat_id": CHANNEL,
            "user_id": chat_id
        })
        status = r.json().get("result", {}).get("status", "")
        return status in ["member", "administrator", "creator"]
    except:
        return False

# ── Webhook ──────────────────────────────────────────────────────
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.json
    msg = data.get("message", {})
    cb = data.get("callback_query", {})

    # معالجة callback (زر تحقق من الاشتراك)
    if cb:
        chat_id = str(cb["from"]["id"])
        user_name = cb["from"].get("first_name", "مجهول")
        if cb.get("data") == "check_sub":
            handle_generate(chat_id, user_name)
        requests.post(f"{TG}/answerCallbackQuery",
            json={"callback_query_id": cb["id"]})
        return "ok"

    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = msg.get("text", "").strip()
    user_name = msg.get("from", {}).get("first_name", "مجهول")

    if not chat_id or not text:
        return "ok"

    if text in ["/generate", "/start"]:
        if text == "/start":
            send(chat_id, (
                f"👋 أهلاً <b>{user_name}</b> في بوت TIKRITI\n\n"
                f"أرسل /generate للحصول على كود الأداة"
            ))
        else:
            handle_generate(chat_id, user_name)

    return "ok"

def handle_generate(chat_id, user_name):
    # 1. تحقق من الاشتراك
    if not is_subscribed(chat_id):
        send(chat_id,
            "⛔ يجب الاشتراك في القناة أولاً للحصول على الكود:",
            keyboard=[[
                {"text": "📲 اشترك في القناة", "url": f"https://t.me/tikriti99"},
                {"text": "✅ تحققت من اشتراكي", "callback_data": "check_sub"}
            ]]
        )
        return

    db = load_db()
    codes = db.get("codes", {})
    users = db.get("users", {})

    # 2. تحقق إذا المستخدم عنده كود قديم
    if chat_id in users:
        old_code = users[chat_id]
        old_data = codes.get(old_code, {})
        r1 = max(0, 2 - old_data.get("used1", 0))
        r2 = max(0, 2 - old_data.get("used2", 0))
        send(chat_id, (
            f"⚠️ عندك كود سابق:\n\n"
            f"🔑 <code>{old_code}</code>\n\n"
            f"• FPS متبقية: {r1}\n"
            f"• آيباد متبقية: {r2}\n\n"
            f"كل مستخدم يحصل على كود واحد فقط."
        ))
        return

    # 3. أنشئ كود جديد
    code = make_code()
    codes[code] = {"used1": 0, "used2": 0, "cnt1": 0, "cnt2": 0, "owner": chat_id}
    users[chat_id] = code
    db["codes"] = codes
    db["users"] = users
    save_db(db)

    send(chat_id, (
        f"🎬 <b>TIKRITI — كودك الجديد</b>\n\n"
        f"🔑 <code>{code}</code>\n\n"
        f"✅ يمنحك هذا الكود:\n"
        f"• محاولتين في أداة تحويل FPS\n"
        f"• محاولتين في أداة آيباد\n\n"
        f"📌 انسخ الكود وأدخله في الأداة\n\n"
        f"⚠️ <i>كل مستخدم يحصل على كود واحد فقط</i>"
    ))

    if chat_id != ADMIN_ID:
        send(ADMIN_ID, f"📋 كود جديد\nالكود: <code>{code}</code>\nلـ: {user_name} ({chat_id})")

@app.route("/")
def home():
    return "TIKRITI Bot is running ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
