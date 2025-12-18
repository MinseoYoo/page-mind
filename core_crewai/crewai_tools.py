"""
CrewAI Tools for Multi-Agent System
외부 API 호출 및 데이터 처리용 Tool만 포함
"""

from crewai.tools import tool
import json
import requests
from .config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET


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

