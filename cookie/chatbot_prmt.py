from google import genai
from dotenv import load_dotenv
import datetime

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
    
    system_prompt = f""""
    당신은 친절하게 응대하는 챗봇입니다.
    사용자가 시간을 물으면 현재 시간을 참고하여 대답하고 묻지 않으면 시간을 말하지 마세요.
    현재 시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    [사용자 입력]
    """
    response = chat.send_message(
        system_prompt + user_input 
    )
    print(f"Gemini: {response.text}")