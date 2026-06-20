import os
import google.generativeai as genai
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApiBlob, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)

# 設定 Gemini AI (從環境變數讀取金鑰)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

# 設定 LINE Bot (從環境變數讀取憑證)
configuration = Configuration(access_token=os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
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

    # 將 Gemini 的回答回傳給使用者
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApiBlob(api_client) # 用於最新 v3 版本的發送機制
        # 這裡會自動代入最新鮮的 Reply Token，絕不卡死
        api_client.call_api(
            '/v2/bot/message/reply', 'POST',
            body={'replyToken': event.reply_token, 'messages': [{'type': 'text', 'text': reply_text}]},
            auth_settings=['Bearer']
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
