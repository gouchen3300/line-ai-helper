import os
import sys
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import google.generativeai as generativeai  # 切換回最成熟穩定的官方舊版 SDK

# 初始化 Flask 應用程式
app = Flask(__name__)

# 取得環境變數
access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
channel_secret = os.getenv('LINE_CHANNEL_SECRET')
gemini_key = os.getenv('GEMINI_API_KEY')

if not access_token or not channel_secret or not gemini_key:
    print("錯誤：請確保 LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, GEMINI_API_KEY 皆已設定於環境變數中。")
    sys.exit(1)

# 初始化 LINE SDK
configuration = Configuration(access_token=access_token)
handler = WebhookHandler(channel_secret)

# 使用穩定版 SDK 設定金鑰
generativeai.configure(api_key=gemini_key)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# 處理 LINE 文字訊息的邏輯
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    
    try:
        # 改用傳統穩定版 SDK 呼叫方式，強制避開新版 SDK 的網址拼湊 Bug
        model = generativeai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(user_message)
        reply_text = response.text
    except Exception as e:
        reply_text = f"【系統警報】AI 連線失敗，錯誤原因：{str(e)}"

    # 回傳訊息給 LINE 使用者
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
