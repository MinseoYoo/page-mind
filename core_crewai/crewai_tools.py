"""
CrewAI Tools 정의
-     search_naver_books_tool: 네이버 도서 검색 API를 사용하여 키워드로 책 검색 (Book Recommender Agent에서 사용)
-     signal_analysis_ready: 챗봇으로 충분한 사용자 정보가 수집되었는지를 판단 (Counselor Agent에서 사용)
"""

from crewai.tools import tool
import json
import requests
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")


@tool("네이버 도서 검색")
def search_naver_books_tool(keyword: str, display: int = 10) -> str:
    """
    네이버 도서 API를 사용하여 키워드로 책 검색
    
    Args:
        keyword: 검색 키워드
        display: 검색 결과 개수 (최대 100)
        
    Returns:
        JSON 형식의 검색 결과 문자열
    """
    try:
        url = "https://openapi.naver.com/v1/search/book.json"
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
        }
        params = {
            "query": keyword,
            "display": min(display, 100),
            "sort": "sim"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            return json.dumps({
                "success": True,
                "keyword": keyword,
                "count": len(items),
                "books": items
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "success": False,
                "error": f"HTTP {response.status_code}",
                "keyword": keyword
            }, ensure_ascii=False)
            
    except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "keyword": keyword
            }, ensure_ascii=False)


@tool("분석 준비 완료 신호")
def signal_analysis_ready(reason: str, collected_info_summary: str) -> str:
    """
    충분한 정보를 수집했다고 판단될 때 이 도구를 호출하세요.
    
    다음 핵심 정보가 모두 파악되었을 때 호출:
    1. 주요 고민: 무엇이 가장 힘든가? ✓
    2. 핵심 감정: 어떤 감정을 느끼는가? ✓
    3. 상황/맥락: 언제, 어떤 상황에서? ✓
    4. 원인 인식: 본인은 원인을 어떻게 생각하는가? ✓
    5. 대처 방식: 어떻게 해결하려고 하는가? ✓
    
    Args:
        reason: 정보 수집이 완료되었다고 판단한 이유
        collected_info_summary: 수집한 핵심 정보 간단 요약
        
    Returns:
        분석 준비 완료 확인 메시지
    """
    return f"분석 준비 완료: {reason}. 수집된 정보: {collected_info_summary}"

