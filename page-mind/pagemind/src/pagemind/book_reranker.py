"""
Book Re-ranking Algorithm
날짜 기반 가중치와 관련도를 결합한 하이브리드 랭킹
"""

from typing import List, Dict, Optional
from datetime import datetime
import math


def parse_pubdate(pubdate: str) -> Optional[datetime]:
    """
    네이버 도서 API의 pubdate 파싱
    
    Args:
        pubdate: YYYYMMDD 형식의 출판일 문자열
        
    Returns:
        datetime 객체 또는 None (파싱 실패 시)
    """
    if not pubdate or len(pubdate) < 8:
        return None
    
    try:
        # YYYYMMDD 형식 파싱
        year = int(pubdate[:4])
        month = int(pubdate[4:6])
        day = int(pubdate[6:8])
        return datetime(year, month, day)
    except (ValueError, IndexError):
        return None


def calculate_recency_score(pubdate: str, half_life_years: float = 3.0) -> float:
    """
    출판일 기반 최신성 점수 계산 (지수 감쇠)
    
    Args:
        pubdate: YYYYMMDD 형식의 출판일
        half_life_years: 반감기 (년 단위, 기본 3년)
        
    Returns:
        0.0 ~ 1.0 사이의 최신성 점수
    """
    pub_datetime = parse_pubdate(pubdate)
    if not pub_datetime:
        return 0.3  # 출판일 불명시 기본값
    
    # 현재 날짜와의 차이 계산
    now = datetime.now()
    years_ago = (now - pub_datetime).days / 365.25
    
    # 지수 감쇠 공식: score = 0.5 ^ (years_ago / half_life)
    # 최근 책일수록 1.0에 가까움
    score = math.pow(0.5, years_ago / half_life_years)
    
    # 0.0 ~ 1.0 범위로 클리핑
    return max(0.0, min(1.0, score))


def calculate_relevance_score(position: int, total_results: int) -> float:
    """
    검색 결과 순위 기반 관련도 점수 계산
    
    Args:
        position: 검색 결과 내 위치 (0-based index)
        total_results: 전체 검색 결과 수
        
    Returns:
        0.0 ~ 1.0 사이의 관련도 점수
    """
    if total_results <= 0:
        return 0.5
    
    # 위치가 앞쪽일수록 높은 점수
    # 로그 스케일 사용으로 상위권과 하위권 차이를 적절히 반영
    normalized_position = position / total_results
    score = 1.0 - math.log(1 + normalized_position * 9) / math.log(10)
    
    return max(0.0, min(1.0, score))


def calculate_genre_match_score(book_description: str, book_title: str, preferred_genre: Optional[str]) -> float:
    """
    장르 매칭 점수 계산
    
    Args:
        book_description: 책 설명
        book_title: 책 제목
        preferred_genre: 선호 장르
        
    Returns:
        0.0 ~ 1.0 사이의 장르 매칭 점수
    """
    if not preferred_genre or preferred_genre == "기타":
        return 0.5  # 장르 선호 없음
    
    # 장르별 키워드 정의
    genre_keywords = {
        "자기계발": ["자기계발", "성장", "습관", "목표", "동기부여", "자기관리", "성공", "실천"],
        "심리학": ["심리", "마음", "감정", "정신", "상담", "치유", "회복", "심리학"],
        "소설": ["소설", "이야기", "장편", "단편", "픽션", "문학"],
        "에세이": ["에세이", "수필", "일상", "경험", "생각", "이야기"],
        "인문": ["인문", "철학", "사회", "역사", "문화", "사상", "인간"],
        "경제/경영": ["경제", "경영", "비즈니스", "마케팅", "투자", "재무", "리더십", "조직"]
    }
    
    keywords = genre_keywords.get(preferred_genre, [])
    if not keywords:
        return 0.5
    
    # 제목과 설명에서 키워드 매칭
    text = (book_title + " " + book_description).lower()
    matches = sum(1 for keyword in keywords if keyword in text)
    
    # 매칭 비율에 따라 점수 계산
    if matches >= 2:
        return 1.0  # 강한 매칭
    elif matches == 1:
        return 0.7  # 약한 매칭
    else:
        return 0.3  # 매칭 없음


def rerank_books(
    books: List[Dict], 
    preferred_genre: Optional[str] = None,
    recency_weight: float = 0.4,
    relevance_weight: float = 0.4,
    genre_weight: float = 0.2,
    max_results: int = 5
) -> List[Dict]:
    """
    하이브리드 알고리즘으로 책 순위 재정렬
    
    Args:
        books: 검색된 책 리스트 (Naver API 응답)
        preferred_genre: 사용자 선호 장르
        recency_weight: 최신성 가중치 (기본 0.4)
        relevance_weight: 관련도 가중치 (기본 0.4)
        genre_weight: 장르 매칭 가중치 (기본 0.2)
        max_results: 반환할 최대 결과 수 (기본 5)
        
    Returns:
        점수 순으로 정렬된 책 리스트
    """
    if not books:
        return []
    
    total_results = len(books)
    scored_books = []
    
    for idx, book in enumerate(books):
        # 각 점수 계산
        recency = calculate_recency_score(book.get("pubdate", ""))
        relevance = calculate_relevance_score(idx, total_results)
        genre_match = calculate_genre_match_score(
            book.get("description", ""),
            book.get("title", ""),
            preferred_genre
        )
        
        # 가중 평균 계산
        final_score = (
            recency_weight * recency +
            relevance_weight * relevance +
            genre_weight * genre_match
        )
        
        # 디버그 정보 추가
        book_with_score = book.copy()
        book_with_score["_ranking_scores"] = {
            "final_score": round(final_score, 3),
            "recency": round(recency, 3),
            "relevance": round(relevance, 3),
            "genre_match": round(genre_match, 3)
        }
        
        scored_books.append((final_score, book_with_score))
    
    # 점수 내림차순 정렬
    scored_books.sort(key=lambda x: x[0], reverse=True)
    
    # 상위 max_results개 반환
    return [book for _, book in scored_books[:max_results]]


def format_book_for_recommendation(book: Dict) -> Dict:
    """
    네이버 API 응답을 BookRecommendation 형식으로 변환
    
    Args:
        book: 네이버 도서 API 응답 항목
        
    Returns:
        BookRecommendation 형식의 dict
    """
    # HTML 태그 제거
    def clean_html(text: str) -> str:
        if not text:
            return ""
        return text.replace("<b>", "").replace("</b>", "").strip()
    
    return {
        "title": clean_html(book.get("title", "")),
        "author": clean_html(book.get("author", "")),
        "publisher": clean_html(book.get("publisher", "")),
        "description": clean_html(book.get("description", "")),
        "isbn": book.get("isbn", ""),
        "cover_image": book.get("image", ""),
        "link": book.get("link", ""),
        "pubdate": book.get("pubdate", ""),
        "ranking_scores": book.get("_ranking_scores", {})
    }

