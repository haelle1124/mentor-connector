"""Mentor Connector: 내 고민을 이해해 줄 선배를 찾아 주는 AI 멘토링 (시연용 MVP)."""

import csv
from datetime import datetime
from pathlib import Path

import streamlit as st

from matching import has_crisis_signal, load_mentors, recommend

APPLICATIONS_PATH = Path(__file__).parent / "data" / "applications.csv"
APPLICATION_FIELDS = ["applied_at", "mentor_id", "mentor_alias", "grade", "region",
                      "concern_types", "question", "match_method"]

GRADES = ["중1", "중2", "중3", "고1", "고2", "고3"]
REGIONS = ["부산", "대구", "광주", "대전", "울산", "세종", "강원", "충북", "충남",
           "전북", "전남", "경북", "경남", "제주"]
FIELDS = ["인문", "사회과학·경영", "교육", "자연과학", "공학·IT", "의약·보건", "예체능", "아직 모르겠어요"]
CONCERN_TYPES = ["학습법", "진로 탐색", "전공 선택", "대학생활"]
STYLES = {
    "차분히 들어주는": "내 얘기를 끝까지 차분히 들어주는 선배",
    "현실적으로 조언하는": "현실적인 정보와 조언을 주는 선배",
    "밝게 응원해 주는": "밝게 응원하고 힘을 주는 선배",
}
MIN_CONCERN_LENGTH = 20

st.set_page_config(page_title="Mentor Connector", page_icon="🤝", layout="centered")


def go(page):
    st.session_state.page = page
    st.rerun()


def mentor_by_id(mentor_id):
    return next(m for m in load_mentors() if m["id"] == mentor_id)


def save_application(mentor, question):
    student = st.session_state.student
    is_new = not APPLICATIONS_PATH.exists()
    APPLICATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    # 고민 자유 서술 원문과 이름·연락처는 저장하지 않는다 (PRD 7장)
    with open(APPLICATIONS_PATH, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=APPLICATION_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow({
            "applied_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mentor_id": mentor["id"],
            "mentor_alias": mentor["alias"],
            "grade": student["grade"],
            "region": student["region"],
            "concern_types": ", ".join(student["concern_types"]),
            "question": question.strip(),
            "match_method": st.session_state.match_method,
        })


def mentor_summary(mentor):
    tag = " :orange-badge[예시 멘토]" if mentor["is_example"] else ""
    st.markdown(f"#### {mentor['alias']} 선배{tag}")
    st.caption(f"성균관대 {mentor['major']} {mentor['year']} · {mentor['hometown']} 출신 · "
               f"{mentor['style']} 스타일")
    st.write(f"“{mentor['intro']}”")


# ---------- 화면 1: 홈 (F1, F9) ----------

def page_home():
    st.title("Mentor Connector")
    st.subheader("내 고민을 잘 이해해 줄 선배를 찾아 드려요")
    st.write(
        "공부 방법, 진로, 전공 선택, 대학생활까지. 고민을 적어 주면 AI가 "
        "비슷한 길을 먼저 걸어 본 성균관대 선배를 추천해 드려요."
    )
    if st.button("내 고민에 맞는 선배 찾기", type="primary", width="stretch"):
        go("input")

    with st.expander("전체 멘토 둘러보기"):
        for mentor in load_mentors():
            with st.container(border=True):
                mentor_summary(mentor)
                st.write(f"멘토링 분야: {', '.join(mentor['topics'])}")


# ---------- 화면 2: 고민 입력 (F2) ----------

def page_input():
    st.title("고민을 들려주세요")
    st.write("자세히 적을수록 나와 잘 맞는 선배를 찾을 수 있어요.")

    saved = st.session_state.get("student", {})
    with st.form("concern_form"):
        col1, col2 = st.columns(2)
        grade = col1.selectbox("학년", GRADES, index=GRADES.index(saved.get("grade", "고1")))
        region = col2.selectbox("지역", REGIONS, index=REGIONS.index(saved.get("region", "부산")))
        interests = st.multiselect("관심 분야 (여러 개 선택 가능)", FIELDS, default=saved.get("interests", []),
                                   placeholder="선택하세요")
        major_text = st.text_input("관심 있는 전공이나 직업 (선택)", value=saved.get("major_text", ""),
                                   placeholder="예: 경영학과, 개발자, 선생님")
        concern_types = st.multiselect("어떤 고민인가요? (여러 개 선택 가능)", CONCERN_TYPES,
                                       default=saved.get("concern_types", []), placeholder="선택하세요")
        concern_text = st.text_area(
            "고민을 자유롭게 적어 주세요",
            value=saved.get("concern_text", ""),
            height=150,
            placeholder="예: 경영학과에 관심은 있는데 주변에 물어볼 사람이 없어요. "
                        "요즘 성적도 떨어져서 불안해요.",
        )
        style_label = st.radio("어떤 선배와 이야기하고 싶나요?", list(STYLES.values()),
                               index=list(STYLES).index(saved.get("preferred_style", "차분히 들어주는")))
        submitted = st.form_submit_button("선배 추천받기", type="primary", width="stretch")

    if submitted:
        errors = []
        if not concern_types:
            errors.append("고민 유형을 하나 이상 골라 주세요.")
        if len(concern_text.strip()) < MIN_CONCERN_LENGTH:
            errors.append(f"고민을 {MIN_CONCERN_LENGTH}자 이상 적어 주세요. "
                          f"(지금 {len(concern_text.strip())}자)")
        if errors:
            for e in errors:
                st.error(e)
        else:
            student = {
                "grade": grade,
                "region": region,
                "interests": interests,
                "major_text": major_text.strip(),
                "concern_types": concern_types,
                "concern_text": concern_text.strip(),
                "preferred_style": next(k for k, v in STYLES.items() if v == style_label),
            }
            st.session_state.student = student
            with st.spinner("고민을 읽고 잘 맞는 선배를 찾고 있어요..."):
                recs, method = recommend(student, load_mentors())
            st.session_state.recommendations = recs
            st.session_state.match_method = method
            st.session_state.crisis = has_crisis_signal(student["concern_text"])
            go("result")

    st.caption("멘토는 경험을 나누고 응원하는 대학생 선배예요. 진단, 치료, 심리상담은 하지 않아요.")
    st.caption("입력한 내용은 AI 추천에만 사용되고, 고민 내용은 저장하지 않아요.")
    if st.button("← 처음으로"):
        go("home")


# ---------- 화면 3: 추천 결과 (F5, F6, F8) ----------

@st.dialog("멘토링 신청하기")
def apply_dialog(mentor_id):
    mentor = mentor_by_id(mentor_id)
    st.write(f"**{mentor['alias']} 선배**에게 멘토링을 신청할게요.")
    question = st.text_input("선배에게 가장 먼저 묻고 싶은 질문 (선택)",
                             placeholder="예: 성적이 떨어졌을 때 어떻게 다시 시작했어요?")
    if st.button("신청하기", type="primary", width="stretch"):
        save_application(mentor, question)
        st.session_state.applied_mentor_id = mentor_id
        go("done")


def page_result():
    if "recommendations" not in st.session_state:
        go("input")

    if st.session_state.crisis:
        st.error(
            "**힘든 마음을 적어 줘서 고마워요.**\n\n"
            "지금 마음이 많이 힘들다면 전문 상담사와 이야기해 보세요.\n\n"
            "- 청소년상담 **1388** (전화·문자·카카오톡)\n"
            "- 자살예방상담 **109**\n\n"
            "24시간, 무료로 이야기를 들어줘요."
        )

    st.title("이런 선배를 추천해요")
    if st.session_state.match_method == "ai":
        st.caption("AI가 고민을 읽고 추천했어요.")
    else:
        st.caption("기본 추천 방식으로 골랐어요. (AI 연결이 안 될 때 사용해요)")

    for rank, rec in enumerate(st.session_state.recommendations, start=1):
        mentor = mentor_by_id(rec["mentor_id"])
        with st.container(border=True):
            st.markdown(f"**추천 {rank}순위**")
            mentor_summary(mentor)
            st.info(f"**왜 이 선배일까요?** {rec['reason']}")
            st.write(f"**선배의 경험** · {mentor['admission_story']}")
            st.write(f"**멘토링 분야** · {', '.join(mentor['topics'])}")
            if st.button("멘토링 신청하기", key=f"apply_{mentor['id']}", type="primary",
                         width="stretch"):
                apply_dialog(mentor["id"])

    if st.button("← 고민 다시 쓰기"):
        go("input")


# ---------- 화면 4: 신청 완료 (F7) ----------

def page_done():
    mentor = mentor_by_id(st.session_state.applied_mentor_id)
    st.title("신청이 완료됐어요")
    st.success(f"**{mentor['alias']} 선배**에게 멘토링 신청이 전달됐어요.")
    st.write(
        "고민을 꺼내 놓는 것만으로도 이미 한 걸음 나아간 거예요. "
        "선배와 이야기하면서 나만의 길을 천천히 찾아가 봐요. 응원할게요!"
    )
    st.caption("시연 버전에서는 신청 기록만 저장되고, 선배에게 실제 알림은 가지 않아요.")
    if st.button("처음으로", width="stretch"):
        for key in ("student", "recommendations", "match_method", "crisis", "applied_mentor_id"):
            st.session_state.pop(key, None)
        go("home")


# ---------- 숨긴 페이지: 신청 목록 (F10) — 주소 뒤에 ?admin=1 ----------

def page_admin():
    st.title("신청 목록 (팀 확인용)")
    if not APPLICATIONS_PATH.exists():
        st.write("아직 신청이 없어요.")
        return
    with open(APPLICATIONS_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    st.write(f"총 {len(rows)}건")
    st.dataframe(list(reversed(rows)), width="stretch")


PAGES = {"home": page_home, "input": page_input, "result": page_result, "done": page_done}

if st.query_params.get("admin") == "1":
    page_admin()
else:
    PAGES[st.session_state.get("page", "home")]()
