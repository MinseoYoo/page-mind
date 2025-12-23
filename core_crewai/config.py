"""
Configuration management for CrewAI multi-agent system
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# CrewAI Configuration
CREWAI_CONFIG = {
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.7,
    "max_tokens": 4000,
}

# Agent Configuration
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

# Task Configuration
CONVERSATION_MIN_TURNS = 5  # Minimum conversation turns before analysis
AUTO_ANALYZE_THRESHOLD = 5  # Auto-trigger analysis after this many assistant responses

