"""
CrewAI Crew Definition for Psychological Counseling System
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

# Tools import (상대 경로 사용)
from .tools.counselor_tool import signal_analysis_ready
from .tools.book_search_tool import search_naver_books_tool


@CrewBase
class Pagemind():
    """심리 상담 챗봇 + 도서 추천 시스템 Crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def counselor(self) -> Agent:
        """Counselor Agent: 공감적 경청과 데이터 수집"""
        return Agent(
            config=self.agents_config['counselor'],  # type: ignore[index]
            verbose=True,
            tools=[signal_analysis_ready],  # 분석 준비 완료 신호 Tool
        )

    @agent
    def psychological_analyzer(self) -> Agent:
        """Psychological Analyzer Agent: SKILL.md 기반 심리 분석"""
        return Agent(
            config=self.agents_config['psychological_analyzer'],  # type: ignore[index]
            verbose=True,
            tools=[],  # Analyzer는 backstory에 모든 지식이 포함되어 있으므로 Tool 불필요
        )

    @agent
    def book_recommender(self) -> Agent:
        """Book Recommender Agent: 도서 검색 및 추천"""
        return Agent(
            config=self.agents_config['book_recommender'],  # type: ignore[index]
            verbose=True,
            tools=[search_naver_books_tool],  # 네이버 도서 검색 Tool
        )

    @task
    def counseling_task(self) -> Task:
        """Counseling Task: 공감적 대화를 통한 정보 수집"""
        return Task(
            config=self.tasks_config['counseling_task'],  # type: ignore[index]
        )

    @task
    def analysis_task(self) -> Task:
        """Analysis Task: SKILL.md 기반 심리 분석"""
        return Task(
            config=self.tasks_config['analysis_task'],  # type: ignore[index]
        )

    @task
    def book_recommendation_task(self) -> Task:
        """Book Recommendation Task: 도서 검색 및 추천"""
        return Task(
            config=self.tasks_config['book_recommendation_task'],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Pagemind crew"""
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,  # 순차적 워크플로우
            verbose=True,
        )
