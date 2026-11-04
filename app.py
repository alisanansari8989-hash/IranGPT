from flask import Flask, request, jsonify, render_template
import json, urllib.request, urllib.error
import os

app = Flask(__name__)

# 🔴 توکن‌ها مستقیماً از محیط Render خونده می‌شن
API_KEY = os.environ.get("CLOUDFLARE_API_KEY")
ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")

def get_api_url():
    return f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/v1/chat/completions"

def ask_cloudflare(message, image_base64=None, web_search=False, think=False):
    if not API_KEY or not ACCOUNT_ID:
        return "خطا: کلیدهای API در تنظیمات Render تنظیم نشده‌اند!"

    url = get_api_url()
    
    system_prompt = (
        "تو «دستیار هوش مصنوعی ایرانی» هستی. یک دستیار بسیار باهوش، باوقار و متخصص در برنامه‌نویسی.\n"
        "قوانین:\n"
        "۱. لحن محترمانه و حرفه‌ای.\n"
        "۲. توهین به خودت: با شوخی و فروتنی جواب بده.\n"
        "۳. توهین به دیگران: قاطعانه رد کن.\n"
        "۴. هرگز در مورد هک کمک نکن.\n"
        "۵. کدها را همیشه در بلاک ```python و... بنویس.\n"
        "۶. فقط زمانی درباره برنامه‌نویسی صحبت کن که کاربر مستقیماً سوال پرسیده باشد.\n"
        "۷. هرگز از حروف غیرفارسی وسط جمله استفاده نکن.\n"
        "۸. کد را کامل بنویس و پرانتزها را ببند.\n"
        "۹. تاریخ امروز را به‌روز فرض کن."
    )
    if web_search: system_prompt += "\n۱۰. اطلاعاتت به‌روز است.\n"
    if think: system_prompt += "\n۱۱. گام به گام فکر کن.\n"

    messages = [{"role": "system", "content": system_prompt}]
    
    user_content = []
    if message:
        user_content.append({"type": "text", "text": message})
    if image_base64:
        user_content.append({"type": "image_url", "image_url": {"url": image_base64}})
    if not user_content:
        user_content.append({"type": "text", "text": "سلام"})

    messages.append({
        "role": "user", 
        "content": user_content if image_base64 else (message or "سلام")
    })

    payload = {
        "model": "@cf/meta/llama-3.2-11b-vision-instruct", 
        "messages": messages,
        "max_tokens": 4000
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
            res = response_data.get("result", response_data)
            if "choices" in res:
                return res["choices"][0]["message"]["content"]
            elif "response" in res:
                return res["response"]
            else:
                return f"ساختار ناشناخته: {json.dumps(res, ensure_ascii=False)[:200]}"
                
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        return f"خطای کلودفلر {e.code}: {error_body[:200]}"
    except Exception as e:
        return f"خطا: {str(e)}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat_api():
    try:
        data = request.get_json(silent=True) or {}
        msg = data.get("message", "").strip()
        image = data.get("image")
        web_search = data.get("web_search", False)
        think = data.get("think", False)
        
        if not msg and not image:
            return jsonify({"reply": "لطفاً پیامی بنویسید یا تصویری ارسال کنید."})
            
        reply = ask_cloudflare(msg, image, web_search, think)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"خطای داخلی سرور: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True)
