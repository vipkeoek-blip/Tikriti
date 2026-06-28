import os, random, json, logging
import requests
from flask import Flask, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("tikriti-bot")

app = Flask(__name__)

BOT_TOKEN = "8963926734:AAF1MOvh1SdtfC23C2QhI4iZFjoll4Jpb60"
ADMIN_ID = "1743301387"
TG = f"https://api.telegram.org/bot{BOT_TOKEN}"
JBIN_KEY = "$2a$10$GTPka01SaLPehwlSP01DH.k1WwIyh9Ko2GrTYMN91JAjBL2Dk.EIG"
JBIN_API = "https://api.jsonbin.io/v3/b"
BIN_ID = "6a40d3f1da38895dfe0a9368"


def load_db():
    """يحمل قاعدة البيانات من jsonbin. يرفع استثناء صريح بدل الفشل الصامت."""
    try:
        r = requests.get(
            f"{JBIN_API}/{BIN_ID}/latest",
            headers={"X-Master-Key": JBIN_KEY},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json().get("record", {})
        codes = data.get("codes", {})
        fingerprints = data.get("fingerprints", {})
        stats = data.get("stats", {})
        log.info(f"load_db OK -> {len(codes)} codes loaded")
        return codes, fingerprints, stats
    except Exception as e:
        log.error(f"load_db FAILED: {e}")
        # نرفع الاستثناء بدل ما نرجع قاموس فاضي بصمت،
        # لأن قاموس فاضي يخلي البوت يفكر إن المستخدم ما عنده كود ويولّد له كود جديد غلط
        raise


def save_db(codes, fingerprints, stats):
    """يحفظ قاعدة البيانات في jsonbin. يرجع True/False بدل الفشل الصامت."""
    try:
        r = requests.put(
            f"{JBIN_API}/{BIN_ID}",
            headers={
                "Content-Type": "application/json",
                "X-Master-Key": JBIN_KEY,
            },
            json={"codes": codes, "fingerprints": fingerprints, "stats": stats},
            timeout=10,
        )
        r.raise_for_status()
        log.info(f"save_db OK -> {len(codes)} codes saved")
        return True
    except Exception as e:
        log.error(f"save_db FAILED: {e}")
        return False


def make_code():
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    p1 = "".join(random.choices(chars, k=4))
    p2 = "".join(random.choices(chars, k=4))
    return f"TIK-{p1}-{p2}"


def find_existing_code(codes, chat_id):
    """يبحث عن كود مرتبط بهذا المستخدم. يقارن كنص دائماً لتجنب مشاكل النوع."""
    chat_id = str(chat_id)
    for c, d in codes.items():
        if str(d.get("owner")) == chat_id:
            return c, d
    return None, None


def send(chat_id, text):
    try:
        r = requests.post(
            f"{TG}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        log.error(f"send FAILED to {chat_id}: {e}")


@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.json or {}
    msg = data.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = (msg.get("text") or "").strip()
    user_name = msg.get("from", {}).get("first_name", "مجهول")

    if not chat_id or not text:
        return "ok"

    if text == "/generate":
        try:
            codes, fingerprints, stats = load_db()
        except Exception:
            # لو فشل تحميل القاعدة، لا نولّد كود جديد أبداً (تجنب تكرار/فقدان الكود)
            send(
                chat_id,
                "⚠️ حدث خطأ مؤقت في الاتصال بقاعدة البيانات. حاول مرة أخرى بعد قليل.\n"
                "لا تقلق، كودك السابق (إن وجد) لن يتأثر."
            )
            return "ok"

        existing_code, existing_data = find_existing_code(codes, chat_id)

        if existing_code:
            d = existing_data
            r1 = max(0, 2 - d.get("used1", 0))
            r2 = max(0, 2 - d.get("used2", 0))
            log.info(f"user {chat_id} ({user_name}) requested /generate -> existing code {existing_code}")
            send(chat_id, (
                f"🎬 <b>TIKRITI — كودك الحالي</b>\n\n"
                f"🔑 <code>{existing_code}</code>\n\n"
                f"لديك كود واحد فقط لكل حساب.\n"
                f"FPS متبقية: {r1} | آيباد متبقية: {r2}\n\n"
                f"📌 انسخ الكود وأدخله في الأداة"
            ))
            return "ok"

        # لا يوجد كود سابق -> نولّد كوداً جديداً ونحفظه فوراً
        code = make_code()
        codes[code] = {
            "used1": 0, "used2": 0, "cnt1": 0, "cnt2": 0,
            "owner": chat_id, "owner_name": user_name
        }

        saved = save_db(codes, fingerprints, stats)

        if not saved:
            # الحفظ فشل: لا نسلّم المستخدم كوداً قد يضيع، نطلب منه إعادة المحاولة
            send(
                chat_id,
                "⚠️ حدث خطأ مؤقت أثناء حفظ كودك. حاول إرسال /generate مرة أخرى بعد قليل."
            )
            return "ok"

        log.info(f"user {chat_id} ({user_name}) requested /generate -> NEW code {code}")
        send(chat_id, (
            f"🎬 <b>TIKRITI — كودك الجديد</b>\n\n"
            f"🔑 <code>{code}</code>\n\n"
            f"✅ يمنحك هذا الكود:\n"
            f"• محاولتين في أداة تحويل FPS\n"
            f"• محاولتين في أداة آيباد\n\n"
            f"📌 انسخ الكود وأدخله في الأداة\n\n"
            f"⚠️ <i>هذا كودك الوحيد ولا يمكن إصدار كود آخر لهذا الحساب</i>"
        ))

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
