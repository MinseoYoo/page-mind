"""
CrewAI 에이전트 정의
-     Counselor Agent: 챗봇을 통해 사용자의 심리적 상황과 도서 추천에 필요한 데이터를 수집하는 에이전트
    분석과 책 추천에 필요한 정보를 충분히 수집하였는지 여부를 확인하기 위한 tool을 사용
-     Psychological Analyzer Agent: smithery.ai의 심리 분석 skills.md 파일을 참고해서 
    챗봇으로 수집된 사용자의 심리 상태에 대해 분석하는 에이전트트
-     Book Recommender Agent: 분석에서 식별된 심리적 필요에 맞는 책을 찾아 추천하는 에이전트
    네이버 도서 검색 API를 사용 (tool)
"""
from pathlib import Path
from crewai import Agent
from .crewai_tools import search_naver_books_tool, signal_analysis_ready

# 에이전트 설정 
COUNSELOR_CONFIG = {
    "role": "Empathic Counselor and Data Collector",
    "goal": "Gather comprehensive user information through empathic listening for psychological analysis and book recommendations",
    "verbose": True,
    "allow_delegation": False,
}

ANALYZER_CONFIG = {
    "role": "Expert Psychological Analyst",
    "goal": "Analyze conversations using rigorous psychological frameworks from SKILL.md to provide comprehensive psychological insights",
    "verbose": True,
    "allow_delegation": False,
}

RECOMMENDER_CONFIG = {
    "role": "Bibliotherapy Specialist",
    "goal": "Find and recommend books that match psychological needs identified in the analysis",
    "verbose": True,
    "allow_delegation": False,
}


def _load_prompt(filename: str) -> str:
    """text_prompts 디렉토리에서 프롬프트 텍스트 로드"""
    prompt_dir = Path(__file__).parent / "text_prompts"
    prompt_path = prompt_dir / filename
    return prompt_path.read_text(encoding="utf-8").strip()


def create_counselor_agent() -> Agent:
    """

    """
    
    backstory = _load_prompt("counselor_backstory.txt")
    
    return Agent(
        role=COUNSELOR_CONFIG["role"],
        goal=COUNSELOR_CONFIG["goal"],
        backstory=backstory,
        verbose=COUNSELOR_CONFIG["verbose"],
        allow_delegation=COUNSELOR_CONFIG["allow_delegation"],
        llm="anthropic/claude-sonnet-4-20250514",
        tools=[signal_analysis_ready],  
    )


def create_psychological_analyzer_agent() -> Agent:
    backstory = _load_prompt("analyzer_backstory.txt")
    
    return Agent(
        role=ANALYZER_CONFIG["role"],
        goal=ANALYZER_CONFIG["goal"],
        backstory=backstory,
        verbose=ANALYZER_CONFIG["verbose"],
        allow_delegation=ANALYZER_CONFIG["allow_delegation"],
        llm="anthropic/claude-sonnet-4-20250514",
        tools=[],
    )


def create_book_recommender_agent() -> Agent:
    backstory = _load_prompt("recommender_backstory.txt")
    
    return Agent(
        role=RECOMMENDER_CONFIG["role"],
        goal=RECOMMENDER_CONFIG["goal"],
        backstory=backstory,
        verbose=RECOMMENDER_CONFIG["verbose"],
        allow_delegation=RECOMMENDER_CONFIG["allow_delegation"],
        llm="anthropic/claude-sonnet-4-20250514",
        tools=[search_naver_books_tool],
    )

