"""
CrewAI Orchestrator - 멀티 에이전트 워크플로우 관리
완전한 CrewAI 기반 구현
"""

from typing import List, Dict, Tuple, Optional
from crewai import Crew, Process
import json

from .agents import (
    create_counselor_agent,
    create_psychological_analyzer_agent,
    create_book_recommender_agent
)
from .tasks import (
    create_counseling_task,
    create_analysis_task,
    create_book_recommendation_task
)
from .models import PsychologicalSummary, BookRecommendation
from .book_reranker import rerank_books, format_book_for_recommendation


class CrewOrchestrator:
    """
    CrewAI 기반 멀티 에이전트 오케스트레이터
    
    순차적 워크플로우:
    1. Counselor Agent: 대화 및 데이터 수집 (CrewAI Agent 사용)
    2. Psychological Analyzer Agent: SKILL.md 기반 심리 분석 (CrewAI Crew 사용)
    3. Book Recommender Agent: 도서 검색 및 추천 (CrewAI Crew 사용)
    """
    
    def __init__(self):
        """오케스트레이터 초기화"""
        # CrewAI Agents (지연 초기화)
        self.counselor_agent = None
        self.analyzer_agent = None
        self.recommender_agent = None
        
        # 대화 상태
        self.conversation_history: List[Dict] = []
    
    def _initialize_agents(self):
        """에이전트 초기화 (지연 초기화)"""
        if self.counselor_agent is None:
            self.counselor_agent = create_counselor_agent()
            self.analyzer_agent = create_psychological_analyzer_agent()
            self.recommender_agent = create_book_recommender_agent()
    
    def chat(self, user_message: str, history: List[Dict]) -> tuple[str, bool]:
        """
        Counselor Agent와 대화 (단일 턴) - CrewAI 사용
        
        Args:
            user_message: 사용자 메시지
            history: 대화 기록
            
        Returns:
            (상담사 응답, 분석 준비 완료 여부)
        """
        self._initialize_agents()
        
        # 메타데이터 제거하여 Anthropic API 호환성 보장
        messages = []
        for msg in history:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        messages.append({"role": "user", "content": user_message})
        
        # CrewAI Task 생성
        counseling_task = create_counseling_task(
            self.counselor_agent,
            user_message,
            messages
        )
        
        # Crew 생성 및 실행
        crew = Crew(
            agents=[self.counselor_agent],
            tasks=[counseling_task],
            process=Process.sequential,
            verbose=False  # 대화는 verbose 끄기 (너무 많은 출력 방지)
        )
        
        # Crew 실행
        result = crew.kickoff()
        response = str(result).strip()
        
        # Tool 호출 확인 (signal_analysis_ready)
        # CrewAI의 실행 결과에서 Tool 호출 확인
        analysis_ready = False
        
        # CrewAI 결과에서 Tool 사용 여부 확인
        # result 객체에서 tasks를 확인하여 Tool 호출 여부 판단
        try:
            # CrewAI는 실행 결과에 Tool 호출 정보를 포함
            # result 객체의 속성을 확인
            if hasattr(result, 'tasks') and result.tasks:
                for task in result.tasks:
                    if hasattr(task, 'agent') and hasattr(task, 'output'):
                        output = str(task.output)
                        # signal_analysis_ready Tool이 호출되었는지 확인
                        if "분석 준비 완료" in output or "signal_analysis_ready" in output.lower():
                            analysis_ready = True
                            break
        except Exception:
            # Tool 확인 실패 시 응답 내용으로 판단
            if "충분한 정보" in response or "분석 준비" in response:
                analysis_ready = True
        
        # 대화 기록 업데이트
        self.conversation_history = messages + [{"role": "assistant", "content": response}]
        
        return response, analysis_ready
    
    def analyze_conversation(self, messages: List[Dict]) -> PsychologicalSummary:
        """
        Psychological Analyzer Agent를 사용한 분석 (CrewAI Crew 사용)
        
        Args:
            messages: 대화 메시지 리스트
            
        Returns:
            PsychologicalSummary 객체
        """
        self._initialize_agents()
        
        # CrewAI Task 생성
        analysis_task = create_analysis_task(self.analyzer_agent, messages)
        
        # Crew 생성 및 실행
        crew = Crew(
            agents=[self.analyzer_agent],
            tasks=[analysis_task],
            process=Process.sequential,
            verbose=True
        )
        
        # Crew 실행
        result = crew.kickoff()
        
        # 결과 파싱 (JSON 형식으로 반환됨)
        result_text = str(result)
        
        # JSON 추출
        try:
            if "```json" in result_text:
                json_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                json_text = result_text.split("```")[1].split("```")[0].strip()
            else:
                # JSON이 직접 포함된 경우
                start_idx = result_text.find("{")
                end_idx = result_text.rfind("}") + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_text = result_text[start_idx:end_idx]
                else:
                    raise ValueError("JSON을 찾을 수 없습니다")
            
            analysis_data = json.loads(json_text)
            
            # PsychologicalSummary 객체 생성
            return PsychologicalSummary(
                main_concerns=analysis_data.get("main_concerns", []),
                emotions=analysis_data.get("emotions", []),
                cognitive_patterns=analysis_data.get("cognitive_patterns", []),
                recommendations=analysis_data.get("recommendations", []),
                keywords=analysis_data.get("keywords", []),
                genre=None  # 장르는 나중에 설정됨
            )
        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON 파싱 오류: {e}")
            print(f"원본 결과: {result_text}")
            # CrewAI만 사용하므로 예외 발생
            raise ValueError(f"심리 분석 결과 파싱 실패: {e}\n원본 결과: {result_text[:500]}")
    
    def recommend_books_from_summary(
        self, 
        summary: PsychologicalSummary, 
        max_books: int = 5
    ) -> List[BookRecommendation]:
        """
        Book Recommender Agent를 사용한 도서 추천 (알고리즘 기반 재정렬)
        
        Args:
            summary: 심리 분석 결과
            max_books: 최대 추천 도서 수
            
        Returns:
            BookRecommendation 객체 리스트
        """
        self._initialize_agents()
        
        # 분석 결과를 dict로 변환
        analysis_dict = {
            "main_concerns": summary.main_concerns,
            "emotions": summary.emotions,
            "cognitive_patterns": summary.cognitive_patterns,
            "recommendations": summary.recommendations,
            "keywords": summary.keywords
        }
        
        # CrewAI Task 생성 (장르 포함)
        recommendation_task = create_book_recommendation_task(
            self.recommender_agent, 
            analysis_dict,
            preferred_genre=summary.genre
        )
        
        # Crew 생성 및 실행
        crew = Crew(
            agents=[self.recommender_agent],
            tasks=[recommendation_task],
            process=Process.sequential,
            verbose=True
        )
        
        # Crew 실행 - 모든 검색 결과 수집
        result = crew.kickoff()
        
        # 결과 파싱
        result_text = str(result)
        
        try:
            # JSON 추출
            if "```json" in result_text:
                json_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                json_text = result_text.split("```")[1].split("```")[0].strip()
            else:
                start_idx = result_text.find("{")
                end_idx = result_text.rfind("}") + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_text = result_text[start_idx:end_idx]
                else:
                    raise ValueError("JSON을 찾을 수 없습니다")
            
            search_data = json.loads(json_text)
            all_books = search_data.get("all_books", [])
            
            if not all_books:
                print("검색 결과가 없습니다.")
                return []
            
            print(f"검색된 책: {len(all_books)}권")
            
            # 알고리즘 기반 재정렬 (LLM 대신 Python 로직 사용)
            reranked_books = rerank_books(
                all_books,
                preferred_genre=summary.genre,
                max_results=max_books
            )
            
            print(f"재정렬 후 상위 {len(reranked_books)}권 선택")
            
            # BookRecommendation 객체 리스트 생성
            recommendations = []
            for book_data in reranked_books:
                formatted = format_book_for_recommendation(book_data)
                
                # 추천 이유 생성 (간단한 템플릿 기반)
                relevance_reason = self._generate_relevance_reason(
                    book_data, 
                    summary,
                    formatted.get("ranking_scores", {})
                )
                
                recommendations.append(BookRecommendation(
                    title=formatted.get("title", ""),
                    author=formatted.get("author", ""),
                    publisher=formatted.get("publisher", ""),
                    description=formatted.get("description", ""),
                    isbn=formatted.get("isbn", ""),
                    cover_image=formatted.get("cover_image", ""),
                    link=formatted.get("link", ""),
                    relevance_reason=relevance_reason
                ))
            
            return recommendations
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"JSON 파싱 오류: {e}")
            print(f"원본 결과: {result_text}")
            # CrewAI만 사용하므로 예외 발생
            raise ValueError(f"도서 추천 결과 파싱 실패: {e}\n원본 결과: {result_text[:500]}")
    
    def _generate_relevance_reason(
        self, 
        book: Dict, 
        summary: PsychologicalSummary,
        scores: Dict
    ) -> str:
        """
        템플릿 기반 추천 이유 생성
        
        Args:
            book: 책 정보
            summary: 심리 분석 결과
            scores: 랭킹 점수
            
        Returns:
            추천 이유 문자열
        """
        reasons = []
        
        # 최신성
        if scores.get("recency", 0) > 0.7:
            reasons.append("최신 출간된 책으로")
        
        # 장르 매칭
        if scores.get("genre_match", 0) > 0.7:
            reasons.append(f"{summary.genre} 장르에 적합하며")
        
        # 주요 고민 연결
        if summary.main_concerns:
            concern = summary.main_concerns[0]
            reasons.append(f"'{concern}'에 대한 통찰을 제공합니다")
        
        # 기본 추천 이유
        if not reasons:
            reasons.append("검색 키워드와 높은 관련성을 보이며 도움이 될 수 있습니다")
        
        return " ".join(reasons) + "."
    
    def run_full_counseling_workflow(
        self, 
        initial_message: str, 
        max_conversation_turns: int = 5
    ) -> Tuple[PsychologicalSummary, List[BookRecommendation]]:
        """
        전체 상담 워크플로우 실행 (테스트용)
        
        Sequential:
        1. Counselor: 대화 진행 (max_conversation_turns 턴)
        2. Analyzer: 심리 분석
        3. Recommender: 도서 추천
        
        Args:
            initial_message: 사용자의 첫 메시지
            max_conversation_turns: 최대 대화 턴 수
            
        Returns:
            (PsychologicalSummary, List[BookRecommendation])
        """
        self._initialize_agents()
        
        print(f"\n{'='*60}")
        print("CrewAI 멀티 에이전트 상담 워크플로우 시작")
        print(f"{'='*60}\n")
        
        # 1단계: 상담 (다중 턴 대화)
        print("1단계: Counseling Agent와 대화 중...")
        print(f"{'='*60}\n")
        
        conversation = []
        current_message = initial_message
        
        for turn in range(max_conversation_turns):
            print(f"[Turn {turn + 1}] 사용자: {current_message}")
            
            # Counselor 응답 (CrewAI 사용)
            response, _ = self.chat(current_message, conversation)
            
            print(f"[Turn {turn + 1}] 상담사: {response}\n")
            
            conversation.append({"role": "user", "content": current_message})
            conversation.append({"role": "assistant", "content": response})
            
            # 다음 턴을 위한 사용자 입력 시뮬레이션 (실제로는 Gradio에서 받음)
            if turn < max_conversation_turns - 1:
                # 테스트를 위한 더미 응답
                current_message = f"네, 알겠습니다. (턴 {turn + 2})"
        
        # 2단계: 심리 분석
        print(f"\n{'='*60}")
        print("2단계: Psychological Analyzer Agent 분석 중...")
        print(f"{'='*60}\n")
        
        summary = self.analyze_conversation(conversation)
        
        print("심리 분석 완료:")
        print(f"- 주요 고민: {summary.main_concerns}")
        print(f"- 감정: {summary.emotions}")
        print(f"- 인지 패턴: {summary.cognitive_patterns}")
        print(f"- 권장사항: {summary.recommendations}")
        print(f"- 키워드: {summary.keywords}\n")
        
        # 3단계: 도서 추천
        print(f"{'='*60}")
        print("3단계: Book Recommender Agent 도서 추천 중...")
        print(f"{'='*60}\n")
        
        books = self.recommend_books_from_summary(summary, max_books=5)
        
        print(f"추천 도서 {len(books)}권:")
        for i, book in enumerate(books, 1):
            print(f"\n{i}. {book.title} - {book.author}")
            print(f"   추천 이유: {book.relevance_reason}")
        
        print(f"\n{'='*60}")
        print("워크플로우 완료!")
        print(f"{'='*60}\n")
        
        return summary, books
    
    def run_analysis_and_recommendation(
        self, 
        conversation_history: List[Dict]
    ) -> Tuple[PsychologicalSummary, List[BookRecommendation]]:
        """
        기존 대화에 대한 분석 및 추천 (Gradio 통합용)
        
        Args:
            conversation_history: 대화 기록
            
        Returns:
            (PsychologicalSummary, List[BookRecommendation])
        """
        print("\n분석 및 추천 시작...")
        
        # 1단계: 심리 분석
        summary = self.analyze_conversation(conversation_history)
        print(f"✓ 심리 분석 완료 (키워드: {len(summary.keywords)}개)")
        
        # 2단계: 도서 추천
        books = self.recommend_books_from_summary(summary, max_books=5)
        print(f"✓ 도서 추천 완료 ({len(books)}권)\n")
        
        return summary, books
    
    def get_conversation_history(self) -> List[Dict]:
        """현재 대화 기록 반환"""
        return self.conversation_history
    
    def clear_conversation(self):
        """대화 기록 초기화"""
        self.conversation_history = []
        print("대화 기록이 초기화되었습니다.")


# 싱글톤 인스턴스 (Gradio 앱에서 사용)
orchestrator = CrewOrchestrator()

