import os
from flask import Flask, request, abort
from google import genai
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)

# 使用 2026 年最新 google-genai 寫法初始化客戶端
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# 設定 LINE Bot 憑證
configuration = Configuration(
    access_token=os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"),
    host="https://api.line.me"
)
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    try:
        # 改用最新、最穩定的 gemini-1.5-flash 模型
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=user_message,
        )
        reply_text = response.text
    except Exception as e:
        # 如果還是出錯，把錯誤訊息直接吐在 LINE 上，方便我們一秒抓鬼
        reply_text = f"Gemini 連線失敗，錯誤回報：{str(e)}"

    # 透過 LINE 發送回覆
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
