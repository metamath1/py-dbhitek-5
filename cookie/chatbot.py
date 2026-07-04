from google import genai
from dotenv import load_dotenv

# 0. 환경변수 로딩
load_dotenv()

# Client는 환경 변수 GEMINI_API_KEY를 자동으로 참조합니다.
client = genai.Client()
chat = client.chats.create(model="gemini-3.1-flash-lite")


print("=== 1단계: 최신 SDK 간단한 챗봇 (종료하려면 'exit' 입력) ===")
while True:
    user_input = input("\nUser: ")
    if user_input.lower() == 'exit':
        break
        
    response = chat.send_message(user_input)
    print(f"Gemini: {response.text}")