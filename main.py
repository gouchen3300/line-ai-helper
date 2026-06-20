import os
import sys
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from google import genai

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

# 初始化新版 Google GenAI SDK
genai_client = genai.Client(api_key=gemini_key)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Please check your Channel Secret and Access Token.")
        abort(400)

    return 'OK'

# 處理 LINE 文字訊息的邏輯
@handler.add(event_type='message', message_type='text')
def handle_message(event):
    user_message = event.message.text
    
    try:
        # 使用修正後的完整模型路徑，避免新舊 SDK 衝突導致的 404 錯誤
        response = genai_client.models.generate_content(
            model='publishers/google/models/gemini-1.5-flash',
            contents=user_message,
        )
        reply_text = response.text
    except Exception as e:
        # 發生錯誤時，將錯誤訊息回傳至 LINE 視窗，方便第一時間排查
        reply_text = f"【系統警報】AI 連線失敗，請檢查 Render 紀錄。\n錯誤原因：{str(e)}"
        print(f"Gemini API 呼叫失敗: {str(e)}")

    # 回傳訊息給 LINE 使用者
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
