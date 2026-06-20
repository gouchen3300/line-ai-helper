import os
import sys
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import google.generativeai as generativeai

app = Flask(__name__)

# 取得環境變數
access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
channel_secret = os.getenv('LINE_CHANNEL_SECRET')
gemini_key = os.getenv('GEMINI_API_KEY')

# 初始化 LINE SDK
configuration = Configuration(access_token=access_token)
handler = WebhookHandler(channel_secret)

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
    
    # 【自動監測機制】
    # 檢查環境變數是否真的有讀進來
    if not gemini_key:
        debug_info = "狀態：Render 完全沒讀到 GEMINI_API_KEY 變數！(請檢查 Environment 頁面)"
    else:
        # 安全地遮蔽中間，只顯示頭尾，保護隱私又能對答案
        debug_info = f"狀態：已讀到金鑰，開頭為「{gemini_key[:4]}...」，結尾為「...{gemini_key[-4:]}」"

    try:
        # 設定並呼叫 Gemini
        generativeai.configure(api_key=gemini_key)
        model = generativeai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(user_message)
        reply_text = response.text
    except Exception as e:
        # 失敗時，除了錯誤原因，連同上面的【變數檢查狀態】一起吐回 LINE 畫面
        reply_text = f"【系統診斷報告】\n\n1. {debug_info}\n\n2. 錯誤原因：{str(e)}"

    # 回傳訊息給 LINE
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
