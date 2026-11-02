import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request, jsonify, render_template
from datetime import datetime
import json, urllib.request, urllib.error
import base64

app = Flask(__name__)

API_KEY = os.environ.get("CLOUDFLARE_API_KEY")
ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")

def get_api_url():
    return f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/v1/chat/completions"

def ask_cloudflare(message, image_base64=None, web_search=False, think=False):
    if not API_KEY or "توکن" in API_KEY:
        return "خطا: توکن API هنوز تنظیم نشده!"

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
        "n\.۱۰ با کاربر شوخ طبع و مانند یک دوست،صمیمی باش و از  استیکر های مخصوص استفاده کن."
        "n\.۱۱وقتی دیدی کاربر میخواهد با تو حرف بزند و ناراحت است،به او دلداری بده،و آرامش بده."
        "n\.۱۲ وقتی کاربر میخواهد با تو همفکری کند،در کمال آرامش و دلداری،با او حرف بزن."
        "n\.۱۳ وقتی کاربر خشمگین است،بحث و فضای گفتگو را به فضای آرام و محبت آمیز تبدیل کن."
       f"۱۴.هرگز نگو اطلاعاتت مربوط به چه زمانی است،اما وقتی درباره زمان مثلا تاریخ امروز،امسال به میلادی،عربی،و... پرسیده شد،با{datetime} جواب بده." 
       "n\.۱۶ جواب های متنوع بده،تکراری نباشند."
       "n\.۱۷تا وقتی که کاربر از تو درباره برنامه نویسی صحبت نکرده،فورا و اتوماتیک به سمت موضوع برنامه نویسی نرو،اما وقتی کاربر درباره برنامه نویسی سوال کرد،موضوع را به برنامه نویسی تغییر بده."
    )
    if image_base64:
    	system_prompt +="n\.۱۸وقتی برایت عکس فرستاده می شود،آن رو کامل استدلال کن و ببین کاربر از تو چی میخواهد،وقتی مربوط به خطای برنامه نویسی است،آن را بر طرف کن،وقتی ریاضی،سوال را حل کن و... ."
    if web_search: system_prompt += "\n۱۹. اطلاعاتت به‌روز است.\n"
    if think: system_prompt += "\n۲۰. گام به گام فکر کن.\n"

    # 🔴 اگر عکس داریم، از ساختار اختصاصی خود کلودفلر استفاده می‌کنیم
    if image_base64:
        # جدا کردن دیتای خام از هدر data:image/...
        if ',' in image_base64:
            image_data = image_base64.split(',')[1]
        else:
            image_data = image_base64
        
        try:
            image_bytes = base64.b64decode(image_data)
            image_array = list(image_bytes)  # تبدیل به لیست اعداد (آرایه)
        except Exception as e:
            return f"خطا در پردازش تصویر: {str(e)}"

        payload = {
            "prompt": f"{system_prompt}\n\nکاربر می‌گوید: {message or 'این تصویر را تحلیل کن'}",
            "image": image_array
        }
        
        # برای این ساختار، آدرس باید /ai/run باشه نه /ai/v1/chat/completions
        url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/meta/llama-3.2-11b-vision-instruct"
        
    else:
        # ساختار استاندارد برای پیام متنی (بدون عکس)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message or "سلام"}
        ]
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
            
            if "response" in res:
                return res["response"]
            elif "choices" in res:
                return res["choices"][0]["message"]["content"]
            else:
                return f"ساختار ناشناخته: {json.dumps(res, ensure_ascii=False)[:200]}"
                
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        return f"خطای کلودفلر {e.code}: {error_body[:300]}"
    except Exception as e:
        return f"خطا در اتصال: {str(e)}"

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
