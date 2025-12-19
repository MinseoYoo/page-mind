"""
CrewAI 작업 정의 - 순차적 워크플로우
"""

import os
from pathlib import Path
from crewai import Task
from typing import List


def _load_prompt_template(filename: str) -> str:
    """text_prompts 디렉토리에서 프롬프트 템플릿 로드"""
    prompt_dir = Path(__file__).parent / "text_prompts"
    prompt_path = prompt_dir / filename
    return prompt_path.read_text(encoding="utf-8").strip()


def create_counseling_task(agent, user_message: str, conversation_history: List[dict]) -> Task:
    """
    작업 1: 상담 세션
    
    에이전트: Counselor Agent
    목표: 공감적 대화를 통해 사용자 정보 수집
    """
    
    # 맥락을 위한 대화 기록 포맷팅
    history_text = ""
    if conversation_history:
        history_text = "\n\n=== 이전 대화 ===\n"
        for msg in conversation_history[-10:]:  # 맥락을 위해 마지막 10개 메시지
            role = "사용자" if msg["role"] == "user" else "상담사"
            history_text += f"{role}: {msg['content']}\n"
        history_text += "================\n\n"
    
    # 템플릿 로드 및 변수로 포맷팅
    template = _load_prompt_template("counseling_task_description.txt")
    description = template.format(
        history_text=history_text,
        user_message=user_message
    )
    
    return Task(
        description=description,
        agent=agent,
        expected_output="사용자에게 공감하는 따뜻한 응답과 정보 수집을 위한 질문 (2-4문장)"
    )


def create_analysis_task(agent, conversation_history: List[dict]) -> Task:
    """
    작업 2: 심리 분석
    
    에이전트: Psychological Analyzer Agent
    목표: SKILL.md 6단계 프레임워크를 적용하여 대화 분석
    """
    
    # 분석을 위한 대화 포맷팅
    conversation_text = "\n\n".join([
        f"{'사용자' if m['role'] == 'user' else '상담사'}: {m['content']}"
        for m in conversation_history if m['role'] != 'system'
    ])
    
    # 템플릿 로드 및 변수로 포맷팅
    template = _load_prompt_template("analysis_task_description.txt")
    description = template.format(conversation_text=conversation_text)
    
    return Task(
        description=description,
        agent=agent,
        expected_output="""JSON 형식의 심리 분석 결과:
{
  "main_concerns": [...],
  "emotions": [...],
  "cognitive_patterns": [...],
  "recommendations": [...],
  "keywords": [...]
}"""
    )


def create_book_recommendation_task(agent, analysis_result: dict, preferred_genre: str = None) -> Task:
    """
    작업 3: 도서 검색
    
    에이전트: Book Recommender Agent
    목표: 심리 분석 키워드를 기반으로 도서 검색
    """
    
    keywords = analysis_result.get('keywords', [])
    genre_info = f"\n**선호 장르**: {preferred_genre}" if preferred_genre else ""
    
    # 템플릿 로드 및 변수로 포맷팅
    template = _load_prompt_template("book_recommendation_task_description.txt")
    description = template.format(
        main_concerns=', '.join(analysis_result.get('main_concerns', [])),
        emotions=', '.join(analysis_result.get('emotions', [])),
        keywords=', '.join(keywords),
        genre_info=genre_info,
        keyword1=keywords[0] if len(keywords) > 0 else '',
        keyword2=keywords[1] if len(keywords) > 1 else '',
        keyword3=keywords[2] if len(keywords) > 2 else ''
    )
    
    return Task(
        description=description,
        agent=agent,
        expected_output="""JSON 형식의 검색된 모든 도서:
{
  "all_books": [
    {
      "title": "...",
      "author": "...",
      "publisher": "...",
      "description": "...",
      "isbn": "...",
      "pubdate": "...",
      "cover_image": "...",
      "link": "..."
    },
    ...
  ]
}"""
    )

