"""
데이터 모델 정의
"""

from pydantic import BaseModel
from typing import List, Optional


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str


class SummaryRequest(BaseModel):
    messages: List[Message]
    conversation_id: str


class PsychologicalSummary(BaseModel):
    main_concerns: List[str]  # 주요 고민
    emotions: List[str]  # 감정 상태
    cognitive_patterns: List[str]  # 인지 패턴
    recommendations: List[str]  # 제안된 전략
    keywords: List[str]  # 도서 검색 키워드


class BookRecommendation(BaseModel):
    title: str
    author: str
    publisher: str
    description: str
    isbn: str
    cover_image: Optional[str]
    link: Optional[str]
    relevance_reason: str  # 왜 이 책을 추천하는지


class CounselingResult(BaseModel):
    summary: PsychologicalSummary
    recommended_books: List[BookRecommendation]
    generated_at: str
