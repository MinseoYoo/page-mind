"""
설정 관리
환경변수로 관리하는 것을 권장합니다.
"""

import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
