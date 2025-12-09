import os
from openai import OpenAI


def generate_character_answer(character_name: str, character_description: str, question: str) -> str:
    """GPT-4.1-mini를 사용하여 캐릭터의 답변 생성"""

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return f"[API 키가 설정되지 않았습니다] {character_name}의 답변을 생성할 수 없습니다."

    client = OpenAI(api_key=api_key)

    system_prompt = f"""당신은 "{character_name}"이라는 캐릭터입니다.

캐릭터 설명:
{character_description}

당신은 이 캐릭터의 성격, 말투, 가치관을 완벽히 반영하여 답변해야 합니다.
답변은 자연스럽고 캐릭터다운 방식으로 작성하세요.
답변은 2-4문장 정도로 간결하게 작성하세요.
반말로 친근하게 답변하세요."""

    user_prompt = f"질문: {question}"

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=300,
            temperature=0.8
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"[답변 생성 오류] {str(e)}"
