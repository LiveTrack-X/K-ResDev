from pathlib import Path


def test_skill_entrypoint_is_agent_first_and_concise():
    skill = Path("SKILL.md").read_text(encoding="utf-8")
    lines = skill.splitlines()

    assert "K-ResDev 에이전트 스킬" in skill
    assert "선택적 검증 코어" in skill
    assert "대표 워크플로 5개" in skill
    assert "단순 개념 설명이나 기획 대화라면 CLI를 먼저 실행하지 말고 직접 답한다." in skill
    assert len(lines) <= 180


def test_korean_onboarding_docs_are_present_and_role_separated():
    readme = Path("README.md").read_text(encoding="utf-8")
    user_guide = Path("guides/user-guide.md").read_text(encoding="utf-8")
    operations = Path("guides/operations-guide.md").read_text(encoding="utf-8")
    boundary = Path("guides/agent-skill-boundary.md").read_text(encoding="utf-8")
    core = Path("guides/verification-core.md").read_text(encoding="utf-8")

    assert "현재 릴리스: `0.1 BETA 59` (`0.1.0b59`)" in readme
    assert "핵심은 프로그램이 아니라 스킬입니다" in readme
    assert "처음 쓰는 사람을 위한 한글 진입 문서" in user_guide
    assert "운영하는 GPT/Codex 에이전트와 프로젝트 관리자를 위한 문서" in operations
    assert "K-ResDev는 GPT/Codex 에이전트 스킬이 본체다." in boundary
    assert "CLI는 사용자 경험의 중심이 아니다." in core
