import os, random
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = "8963926734:AAF1MOvh1SdtfC23C2QhI4iZFjoll4Jpb60"
ADMIN_ID = "1743301387"
CHANNEL = "@tikriti99"
TG = f"https://api.telegram.org/bot{BOT_TOKEN}"
JBIN_KEY = "$2a$10$GTPka01SaLPehwlSP01DH.k1WwIyh9Ko2GrTYMN91JAjBL2Dk.EIG"
JBIN_API = "https://api.jsonbin.io/v3/b"
BIN_ID = "6a40d3f1da38895dfe0a9368"

def load_db():
    try:
        r = requests.get(f"{JBIN_API}/{BIN_ID}/latest",
            headers={"X-Master-Key": JBIN_KEY})
        rec = r.json().get("record", {})
        if "codes" not in rec: rec["codes"] = {}
        if "users" not in rec: rec["users"] = {}
        return rec
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

def make_code():
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    p1 = "".join(random.choices(chars, k=4))
    p2 = "".join(random.choices(chars, k=4))
    return f"TIK-{p1}-{p2}"

def send(chat_id, text, keyboard=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        payload["reply_markup"] = {"inline_keyboard": keyboard}
    requests.post(f"{TG}/sendMessage", json=payload)

def is_subscribed(chat_id):
    # الأدمن دائماً مشترك
    if str(chat_id) == ADMIN_ID:
        return True
    try:
        r = requests.get(f"{TG}/getChatMember", params={
            "chat_id": CHANNEL,
            "user_id": chat_id
        })
        status = r.json().get("result", {}).get("status", "left")
        return status in ["member", "administrator", "creator"]
    except:
        return False

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.json

    # زر "تحققت من اشتراكي"
    cb = data.get("callback_query", {})
    if cb:
        chat_id = str(cb["from"]["id"])
        user_name = cb["from"].get("first_name", "مجهول")
        if cb.get("data") == "check_sub":
            handle_generate(chat_id, user_name)
        requests.post(f"{TG}/answerCallbackQuery",
            json={"callback_query_id": cb["id"]})
        return "ok"

    msg = data.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = msg.get("text", "").strip()
    user_name = msg.get("from", {}).get("first_name", "مجهول")

    if not chat_id or not text:
        return "ok"

    if text == "/start":
        send(chat_id,
            f"👋 أهلاً <b>{user_name}</b>\n\nأرسل /generate للحصول على كود الأداة 🎬"
        )
    elif text == "/generate":
        handle_generate(chat_id, user_name)

    return "ok"

def handle_generate(chat_id, user_name):
    # 1. تحقق الاشتراك
    if not is_subscribed(chat_id):
        send(chat_id,
            "⛔ <b>يجب الاشتراك في القناة أولاً</b>\n\nاشترك ثم اضغط تحققت ✅",
            keyboard=[[
                {"text": "📲 اشترك في القناة", "url": "https://t.me/tikriti99"}
            ],[
                {"text": "✅ تحققت من اشتراكي", "callback_data": "check_sub"}
            ]]
        )
        return

    db = load_db()
    codes = db["codes"]
    users = db["users"]

    # 2. إذا عنده كود سابق — أعطه إياه
    if chat_id in users:
        old_code = users[chat_id]
        old_data = codes.get(old_code, {})
        r1 = max(0, 2 - old_data.get("used1", 0))
        r2 = max(0, 2 - old_data.get("used2", 0))

        if r1 == 0 and r2 == 0:
            # الكود خلص — رسالة اشتراك مدى الحياة
            send(chat_id,
                "🔒 <b>انتهت محاولاتك!</b>\n\n"
                "للحصول على اشتراك <b>مدى الحياة</b> بمحاولات غير محدودة:\n\n"
                "📲 تواصل معنا مباشرة 👇",
                keyboard=[[
                    {"text": "💬 تواصل مع الأدمن", "url": "https://t.me/tikriti99"}
                ]]
            )
        else:
            send(chat_id,
                f"⚠️ <b>عندك كود موجود:</b>\n\n"
                f"🔑 <code>{old_code}</code>\n\n"
                f"• FPS متبقية: {r1}\n"
                f"• آيباد متبقية: {r2}\n\n"
                f"<i>كل مستخدم يحصل على كود واحد فقط</i>"
            )
        return

    # 3. أنشئ كود جديد
    code = make_code()
    codes[code] = {"used1": 0, "used2": 0, "cnt1": 0, "cnt2": 0, "owner": chat_id}
    users[chat_id] = code
    db["codes"] = codes
    db["users"] = users
    save_db(db)

    send(chat_id,
        f"🎬 <b>TIKRITI — كودك الجديد</b>\n\n"
        f"🔑 <code>{code}</code>\n\n"
        f"✅ يمنحك هذا الكود:\n"
        f"• محاولتين في أداة تحويل FPS\n"
        f"• محاولتين في أداة آيباد\n\n"
        f"📌 انسخ الكود وأدخله في الأداة\n\n"
        f"⚠️ <i>كل مستخدم يحصل على كود واحد فقط</i>"
    )

    if chat_id != ADMIN_ID:
        send(ADMIN_ID,
            f"📋 كود جديد صدر\n"
            f"الكود: <code>{code}</code>\n"
            f"لـ: {user_name} ({chat_id})"
        )

@app.route("/")
def home():
    return "TIKRITI Bot is running ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
