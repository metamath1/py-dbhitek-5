import datetime
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 0. 환경변수 로딩
load_dotenv()

# 1. 데모용 후보 함수 정의
def get_current_time(location: str) -> str:
    """특정 지역의 현재 시간을 반환합니다."""
    return f"{location}의 현재 시간은 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 입니다."

def calculate_math(expression: str) -> str:
    """수학 수식을 계산하여 결과를 반환합니다."""
    try:
        return str(eval(expression))
    except Exception as e:
        return f"계산 오류: {e}"

# 2. 최신 SDK Client 생성
client = genai.Client()

# 핵심 수정: automatic_function_calling을 disable=True로 설정하여 자동 실행 방지
chat = client.chats.create(
    model="gemini-3.1-flash-lite",
    config=types.GenerateContentConfig(
        tools=[get_current_time, calculate_math],
        # 내부적으로 함수호출을 자동으로 처리하는 기능 중지
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
    )
)

print("=== 2단계: Agentic 챗봇 (종료하려면 'exit' 입력) ===")
while True:
    user_input = input("\nUser: ")
    if user_input.lower() == 'exit':
        break
        
    # 첫 번째 LLM 호출
    response = chat.send_message(user_input)
    
    # 자동 실행이 비활성화되었으므로, 함수 호출 필요 시 루프 안으로 정상 진입합니다.
    while response.function_calls:
        fc = response.function_calls[0]
        print(f"\n  [시스템 로그] LLM이 함수 호출을 요청했습니다: 함수: {fc.name}, 인수: {fc.args}")
        
        # 함수 이름에 따른 실제 파이썬 함수 실행 매핑
        if fc.name == "get_current_time":
            result = get_current_time(**fc.args)
        elif fc.name == "calculate_math":
            result = calculate_math(**fc.args)
        else:
            result = "알 수 없는 함수입니다."
            
        print(f"  [시스템 로그] 함수 실행 결과: {result}")
        
        # 수동으로 실행한 결과를 다시 모델에게 전송하여 다음 판단(추가 함수 호출 혹은 최종 평문 답변)을 유도
        # 만약 함수 A의 호출 결과를 보고 다시 다른 함수 B를 호출해야 한다고 답변하면
        # 문제 해결을 위해 다양한 단계를 계획하고 순차적으로 수행하는 Agent가 되는 것임
        response = chat.send_message(
            types.Part.from_function_response(
                name=fc.name,
                response={"result": result}
            )
        )
        
    # 함수 호출 프로세스가 끝나고 반환된 최종 평문 답변 출력
    print(f"\nGemini: {response.text}")