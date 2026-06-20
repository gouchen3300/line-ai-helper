import os
import google.generativeai as genai
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)

# 設定 Gemini AI
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

# 設定 LINE Bot 憑證
# 加上 host 參數，徹底杜絕最新版 SDK 出現 NoneType + str 的底層錯誤
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
        # 呼叫 Gemini 產生回應
        response = model.generate_content(user_message)
        reply_text = response.text
    except Exception as e:
        reply_text = "真抱歉，我現在腦袋有點打結，請再跟我說一次！"

    # 修正：改用最標準的 MessagingApi 進行單純的文字回覆
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
