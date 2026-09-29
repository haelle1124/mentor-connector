"""멘토 추천 로직: AI 매칭(F3), 백업 매칭(F4), 위기 표현 감지(F8)."""

import json
import os
import re
from pathlib import Path

MENTORS_PATH = Path(__file__).parent / "data" / "mentors.json"
TOP_N = 3
# 앞 모델이 혼잡(503)하거나 느리면 다음 모델을 시도한다. "-latest" 이름은 구글이 최신 모델로 자동 연결해 준다.
DEFAULT_MODELS = ["gemini-flash-lite-latest", "gemini-flash-latest"]
TIMEOUT_MS = 12_000

# 공백을 뺀 형태로 비교한다 ("죽고 싶다" → "죽고싶다")
CRISIS_KEYWORDS = [
    "죽고싶", "죽어버리", "죽을래", "자살", "자해", "사라지고싶", "없어지고싶",
    "살기싫", "살고싶지않", "뛰어내리", "목숨을끊", "극단적선택",
]


def load_mentors():
    with open(MENTORS_PATH, encoding="utf-8") as f:
        return json.load(f)


def has_crisis_signal(text):
    compact = re.sub(r"\s+", "", text)
    return any(keyword in compact for keyword in CRISIS_KEYWORDS)


# ---------- 백업 매칭 (AI 없이 점수로 추천) ----------

def _score(student, mentor):
    """PRD 6장 점수표: 계열 3점, 고민 유형 2점씩, 스타일 2점, 키워드 1점씩."""
    score = 0
    reasons = []

    major_text = student["major_text"]
    # "경영학과" → "경영" 처럼 끝의 학과/학부/과를 떼고 멘토 전공에 들어 있는지 본다
    stems = [re.sub(r"(학과|학부|과)$", "", w) for w in re.split(r"[\s,·/]+", major_text)]
    same_major = any(len(s) >= 2 and s in mentor["major"] for s in stems)
    if mentor["field"] in student["interests"] or same_major:
        score += 3
        reasons.append(f"관심 있는 {mentor['field']} 계열({mentor['major']}) 선배예요.")

    shared_topics = [t for t in student["concern_types"] if t in mentor["topics"]]
    if shared_topics:
        score += 2 * len(shared_topics)
        reasons.append(f"{', '.join(shared_topics)} 고민을 함께 이야기할 수 있어요.")

    if student["preferred_style"] == mentor["style"]:
        score += 2
        reasons.append(f"원하는 '{mentor['style']}' 스타일의 선배예요.")

    concern = student["concern_text"] + " " + major_text
    hits = [k for k in mentor["keywords"] if k in concern]
    score += len(hits)
    if hits:
        reasons.append(f"'{hits[0]}' 같은 비슷한 경험이 있어요.")

    if not reasons:
        reasons.append("다양한 고민을 들어줄 수 있는 선배예요.")
    return score, " ".join(reasons)


def backup_match(student, mentors):
    scored = []
    for mentor in mentors:
        score, reason = _score(student, mentor)
        scored.append((score, mentor["id"], reason))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [{"mentor_id": mid, "reason": reason} for _, mid, reason in scored[:TOP_N]]


# ---------- AI 매칭 (Gemini) ----------

SYSTEM_PROMPT = """너는 비수도권 중·고등학생에게 잘 맞는 대학생 선배 멘토를 추천하는 도우미다.
학생의 고민 글에서 핵심 고민과 감정을 파악하고, 멘토 목록과 비교해 가장 잘 맞는 멘토 3명을 고른다.

규칙:
- 반드시 멘토 목록에 있는 id만 사용한다. 없는 사람이나 경험을 지어내지 않는다.
- 서로 다른 멘토 3명을 적합한 순서대로 고른다.
- reason은 학생에게 직접 말하듯 따뜻한 존댓말로 2~3문장 쓴다. 학생의 고민을 짧게 공감한 뒤, 멘토의 어떤 경험이 왜 도움이 되는지 말한다.
- 중학생도 이해할 수 있는 쉬운 말을 쓴다.
- 진단하거나 상담하듯 말하지 않는다 (예: "우울증이에요" 금지).
- 아래 JSON 형식으로만 답한다.
{"recommendations": [{"mentor_id": "M01", "reason": "..."}, {"mentor_id": "...", "reason": "..."}, {"mentor_id": "...", "reason": "..."}]}"""


def _get_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    try:
        import streamlit as st
        return st.secrets.get("GEMINI_API_KEY")
    except Exception:
        return None


def _get_models():
    """secrets 또는 환경변수 GEMINI_MODEL(쉼표로 여러 개 가능)이 있으면 그것을, 없으면 기본 목록을 쓴다."""
    value = os.environ.get("GEMINI_MODEL")
    try:
        import streamlit as st
        value = st.secrets.get("GEMINI_MODEL", value)
    except Exception:
        pass
    if value:
        return [m.strip() for m in value.split(",") if m.strip()]
    return DEFAULT_MODELS


def ai_match(student, mentors):
    """Gemini로 추천한다. 키가 없거나 응답이 이상하면 예외를 던진다."""
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다.")

    from google import genai
    from google.genai import types

    mentor_info = [
        {k: m[k] for k in ("id", "major", "field", "year", "hometown", "admission_story", "topics", "style")}
        for m in mentors
    ]
    user_prompt = (
        "[학생 정보]\n"
        + json.dumps({k: v for k, v in student.items()}, ensure_ascii=False)
        + "\n\n[멘토 목록]\n"
        + json.dumps(mentor_info, ensure_ascii=False)
    )

    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=TIMEOUT_MS))
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
        temperature=0.4,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    last_error = None
    for model in _get_models():
        try:
            response = client.models.generate_content(model=model, contents=user_prompt, config=config)
            return _parse_ai_response(response.text, {m["id"] for m in mentors})
        except Exception as e:
            print(f"[{model} 실패] {type(e).__name__}: {str(e)[:200]}")
            last_error = e
    raise last_error


def _parse_ai_response(text, valid_ids):
    data = json.loads(text)
    recs = data["recommendations"]
    result = []
    for rec in recs:
        mid = rec.get("mentor_id")
        reason = (rec.get("reason") or "").strip()
        if mid in valid_ids and reason and mid not in [r["mentor_id"] for r in result]:
            result.append({"mentor_id": mid, "reason": reason})
    if len(result) < TOP_N:
        raise ValueError(f"AI 응답에 올바른 멘토가 {len(result)}명뿐입니다.")
    return result[:TOP_N]


def recommend(student, mentors):
    """AI 매칭을 먼저 시도하고, 실패하면 백업 매칭으로 넘어간다.

    반환값: (추천 목록, 사용한 방식 "ai" 또는 "backup")
    """
    try:
        return ai_match(student, mentors), "ai"
    except Exception as e:
        print(f"[AI 매칭 실패 → 백업 매칭] {type(e).__name__}: {e}")
        return backup_match(student, mentors), "backup"
