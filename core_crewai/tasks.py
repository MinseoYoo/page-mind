"""
CrewAI Task Definitions for Sequential Workflow
"""

from crewai import Task
from typing import List


def create_counseling_task(agent, user_message: str, conversation_history: List[dict]) -> Task:
    """
    Task 1: Counseling Session
    
    Agent: Counselor Agent
    Goal: Engage in empathic conversation to collect user information
    """
    
    # Format conversation history for context
    history_text = ""
    if conversation_history:
        history_text = "\n\n=== 이전 대화 ===\n"
        for msg in conversation_history[-10:]:  # Last 10 messages for context
            role = "사용자" if msg["role"] == "user" else "상담사"
            history_text += f"{role}: {msg['content']}\n"
        history_text += "================\n\n"
    
    description = f"""{history_text}현재 사용자 메시지: {user_message}

위 메시지에 공감적으로 응답하고, 다음 핵심 정보를 파악하기 위한 질문을 하세요:

1. **주요 고민**: 무엇이 가장 힘든가?
2. **핵심 감정**: 어떤 감정을 느끼는가?
3. **상황/맥락**: 언제, 어떤 상황에서?
4. **대처 방식**: 어떻게 해결하려고 하는가?
5. **독서 선호**: 어떤 책을 좋아하는가? (적절한 타이밍에)

**응답 스타일**:
- 2-3문장으로 공감하고 1개의 구체적 질문
- 따뜻하고 자연스러운 대화
- 심리 분석은 하지 말고, 경청과 정보 수집에 집중"""
    
    return Task(
        description=description,
        agent=agent,
        expected_output="사용자에게 공감하는 따뜻한 응답과 정보 수집을 위한 질문 (2-4문장)"
    )


def create_analysis_task(agent, conversation_history: List[dict]) -> Task:
    """
    Task 2: Psychological Analysis
    
    Agent: Psychological Analyzer Agent
    Goal: Apply SKILL.md 6-step framework to analyze conversation
    """
    
    # Format conversation for analysis
    conversation_text = "\n\n".join([
        f"{'사용자' if m['role'] == 'user' else '상담사'}: {m['content']}"
        for m in conversation_history if m['role'] != 'system'
    ])
    
    description = f"""다음 상담 대화를 SKILL.md의 6단계 프레임워크로 분석하세요:

=== 상담 대화 ===
{conversation_text}
===================

## 분석 단계

1. **Define Psychological Phenomenon**: 현상 정의 (행동 패턴, 맥락, 분석 수준, 관련 영역)
2. **Apply Psychological Theories**: 이론 적용 (인지, 사회, 임상 이론 및 메커니즘)
3. **Analyze Cognitive Processes**: 인지 분석 (편향, 사고 패턴, 의사결정, 정보처리)
4. **Examine Emotional and Motivational**: 감정/동기 분석 (감정, 감정조절, 동기, 욕구)
5. **Assess Social and Situational**: 사회/상황 분석 (상황의 힘, 사회적 영향, 집단 역학)
6. **Evaluate Mental Health Dimensions**: 정신건강 평가 (고통 수준, 기능 영향, 위험/보호 요인)

## 출력 형식 (JSON)

{{
  "main_concerns": ["주요 고민 1", "주요 고민 2", ...],
  "emotions": ["감정 1", "감정 2", ...],
  "cognitive_patterns": ["인지 패턴 1", "인지 패턴 2", ...],
  "recommendations": ["권장사항 1", "권장사항 2", ...],
  "keywords": ["키워드1", "키워드2", "키워드3"]
}}

**중요**: 
- keywords는 **정확히 3개**만 생성하세요 (검색 API 제한)
- 사용자의 핵심 니즈를 가장 잘 대표하는 키워드 선택
- 일상적 용어 사용 (예: "외로움", "자존감", "직장스트레스")
- 심리학 전문 용어는 피하세요 (예: "인지왜곡", "투사", "억압")"""
    
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
    Task 3: Book Search
    
    Agent: Book Recommender Agent
    Goal: Search books based on psychological analysis keywords
    """
    
    keywords = analysis_result.get('keywords', [])
    genre_info = f"\n**선호 장르**: {preferred_genre}" if preferred_genre else ""
    
    description = f"""다음 심리 분석 결과를 바탕으로 관련 도서를 검색하세요:

## 심리 분석 결과

**주요 고민**: {', '.join(analysis_result.get('main_concerns', []))}
**감정 상태**: {', '.join(analysis_result.get('emotions', []))}
**검색 키워드**: {', '.join(keywords)}{genre_info}

## 작업

1. **키워드별 검색**: 제공된 3개의 키워드 각각으로 네이버 도서 API 검색
   - 키워드 1: "{keywords[0] if len(keywords) > 0 else ''}"
   - 키워드 2: "{keywords[1] if len(keywords) > 1 else ''}"
   - 키워드 3: "{keywords[2] if len(keywords) > 2 else ''}"

2. **메타데이터 수집**: 각 검색 결과에서 다음 정보를 수집
   - title, author, publisher, description
   - isbn, pubdate (출판일 - 중요!)
   - cover_image, link

3. **중복 제거**: ISBN 기준으로 중복된 책 제거

## 중요

- **모든 검색 결과를 반환** (선택하지 말고 모두 수집)
- **pubdate 필드를 반드시 포함** (재정렬에 사용됨)
- HTML 태그 제거 (예: <b>, </b>)

## 출력 형식 (JSON)

{{
  "all_books": [
    {{
      "title": "책 제목",
      "author": "저자",
      "publisher": "출판사",
      "description": "책 설명",
      "isbn": "ISBN",
      "pubdate": "YYYYMMDD",
      "cover_image": "표지 URL",
      "link": "네이버 도서 링크"
    }},
    ...
  ]
}}"""
    
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

