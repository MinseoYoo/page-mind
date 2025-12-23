#!/usr/bin/env python
"""
심리 상담 챗봇 + 도서 추천 시스템 - CrewAI 실행 파일
"""

import sys
import warnings
from datetime import datetime
from typing import List, Dict
import json

from pagemind.crew import Pagemind

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def run():
    """
    Run the crew with example inputs.
    
    예시: 상담 대화만 실행 (counseling_task)
    전체 워크플로우를 실행하려면 run_full_workflow() 함수를 사용하세요.
    """
    # 예시: 상담 대화 입력 (counseling_task만 실행)
    inputs = {
        'user_message': '요즘 직장에서 스트레스를 많이 받아요.',
        'conversation_context': '=== 이전 대화 ===\n사용자: 요즘 직장에서 스트레스를 많이 받아요.\n================\n\n',
    }

    try:
        # counseling_task만 실행하는 간단한 crew 생성
        from pagemind.crew import Pagemind
        from crewai import Crew, Process
        
        crew_instance = Pagemind()
        crew = Crew(
            agents=[crew_instance.counselor()],
            tasks=[crew_instance.counseling_task()],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff(inputs=inputs)
        print("\n" + "="*60)
        print("Crew 실행 완료!")
        print("="*60)
        print(result)
    except Exception as e:
        raise Exception(f"Crew 실행 중 오류 발생: {e}")


def run_full_workflow():
    """
    전체 워크플로우 실행: 상담 -> 분석 -> 도서 추천
    
    주의: 이 함수는 analysis_task의 출력을 book_recommendation_task에서 사용하므로,
    CrewAI의 자동 컨텍스트 전달 기능을 활용합니다.
    """
    inputs = {
        'user_message': '요즘 직장에서 스트레스를 많이 받아요. 상사가 계속 무리한 요구를 하는데 거절하지 못하겠어요.',
        'conversation_context': '=== 이전 대화 ===\n사용자: 요즘 직장에서 스트레스를 많이 받아요.\n================\n\n',
        'conversation_text': '사용자: 요즘 직장에서 스트레스를 많이 받아요. 상사가 계속 무리한 요구를 하는데 거절하지 못하겠어요.'
    }
    
    try:
        from pagemind.crew import Pagemind
        from crewai import Crew, Process
        
        crew_instance = Pagemind()
        # 전체 워크플로우 실행 (순차적)
        crew = Crew(
            agents=[
                crew_instance.counselor(),
                crew_instance.psychological_analyzer(),
                crew_instance.book_recommender()
            ],
            tasks=[
                crew_instance.counseling_task(),
                crew_instance.analysis_task(),
                crew_instance.book_recommendation_task()
            ],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff(inputs=inputs)
        print("\n" + "="*60)
        print("전체 워크플로우 실행 완료!")
        print("="*60)
        print(result)
        return result
    except Exception as e:
        raise Exception(f"전체 워크플로우 실행 중 오류 발생: {e}")


def run_counseling(user_message: str, conversation_history: List[Dict]) -> str:
    """
    상담 대화 실행 (단일 턴)
    
    Args:
        user_message: 사용자 메시지
        conversation_history: 대화 기록
        
    Returns:
        상담사 응답
    """
    # 대화 기록 포맷팅
    history_text = ""
    if conversation_history:
        history_text = "\n\n=== 이전 대화 ===\n"
        for msg in conversation_history[-10:]:  # 최근 10개 메시지
            role = "사용자" if msg["role"] == "user" else "상담사"
            history_text += f"{role}: {msg['content']}\n"
        history_text += "================\n\n"
    
    inputs = {
        'user_message': user_message,
        'conversation_context': history_text,
    }
    
    try:
        # Counselor Agent만 실행하는 간단한 crew 생성
        from pagemind.crew import Pagemind
        crew_instance = Pagemind()
        
        # counseling_task만 실행
        from crewai import Crew, Process
        crew = Crew(
            agents=[crew_instance.counselor()],
            tasks=[crew_instance.counseling_task()],
            process=Process.sequential,
            verbose=False
        )
        
        result = crew.kickoff(inputs=inputs)
        return str(result).strip()
    except Exception as e:
        raise Exception(f"상담 실행 중 오류 발생: {e}")


def run_analysis(conversation_history: List[Dict]) -> Dict:
    """
    심리 분석 실행
    
    Args:
        conversation_history: 대화 기록
        
    Returns:
        심리 분석 결과 (JSON)
    """
    # 대화 텍스트 포맷팅
    conversation_text = "\n\n".join([
        f"{'사용자' if m['role'] == 'user' else '상담사'}: {m['content']}"
        for m in conversation_history if m['role'] != 'system'
    ])
    
    inputs = {
        'conversation_text': conversation_text,
    }
    
    try:
        from pagemind.crew import Pagemind
        crew_instance = Pagemind()
        
        from crewai import Crew, Process
        crew = Crew(
            agents=[crew_instance.psychological_analyzer()],
            tasks=[crew_instance.analysis_task()],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff(inputs=inputs)
        result_text = str(result)
        
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
        
        return json.loads(json_text)
    except Exception as e:
        raise Exception(f"분석 실행 중 오류 발생: {e}")


def run_book_recommendation(analysis_result: Dict, preferred_genre: str = None) -> List[Dict]:
    """
    도서 추천 실행
    
    Args:
        analysis_result: 심리 분석 결과
        preferred_genre: 선호 장르
        
    Returns:
        검색된 도서 리스트
    """
    keywords = analysis_result.get('keywords', [])
    genre_info = f"\n**선호 장르**: {preferred_genre}" if preferred_genre else ""
    
    inputs = {
        'main_concerns': ', '.join(analysis_result.get('main_concerns', [])),
        'emotions': ', '.join(analysis_result.get('emotions', [])),
        'keywords': ', '.join(keywords),
        'keyword1': keywords[0] if len(keywords) > 0 else '',
        'keyword2': keywords[1] if len(keywords) > 1 else '',
        'keyword3': keywords[2] if len(keywords) > 2 else '',
        'genre_info': genre_info,
    }
    
    try:
        from pagemind.crew import Pagemind
        crew_instance = Pagemind()
        
        from crewai import Crew, Process
        crew = Crew(
            agents=[crew_instance.book_recommender()],
            tasks=[crew_instance.book_recommendation_task()],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff(inputs=inputs)
        result_text = str(result)
        
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
        return search_data.get("all_books", [])
    except Exception as e:
        raise Exception(f"도서 추천 실행 중 오류 발생: {e}")


if __name__ == "__main__":
    run()
