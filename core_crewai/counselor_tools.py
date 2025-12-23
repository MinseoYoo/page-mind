"""
Counselor Agent용 CrewAI Tools
"""

from crewai.tools import tool


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

