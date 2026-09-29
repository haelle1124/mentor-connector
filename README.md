# Mentor Connector

비수도권 중·고등학생의 고민을 AI가 읽고, 잘 맞는 성균관대 선배 멘토를 추천하는 시연용 웹서비스입니다.
기획 문서는 [docs/PRD.md](docs/PRD.md)에 있습니다.

## 파일 구성

| 파일 | 역할 |
| --- | --- |
| `app.py` | 화면 4개 (홈, 고민 입력, 추천 결과, 신청 완료) + 신청 목록 페이지 |
| `matching.py` | AI 매칭(Gemini), 백업 매칭(점수), 위기 표현 감지 |
| `data/mentors.json` | 멘토 10명 (M01·M02 실제 멘토 자리, M03~M10 예시 멘토) |
| `data/applications.csv` | 신청 기록 (실행 중 자동 생성, 깃에 올라가지 않음) |
| `.streamlit/config.toml` | 화면 색상 |

## 내 컴퓨터에서 실행하기

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 http://localhost:8501 이 열립니다.

API 키가 없어도 실행됩니다. 이때는 백업 매칭(점수 방식)으로 추천하고, 결과 화면에 "기본 추천 방식으로 골랐어요"라고 표시됩니다.

## AI 추천 켜기 (Gemini 무료 API)

1. [Google AI Studio](https://aistudio.google.com/)에서 API 키를 발급받습니다.
2. `.streamlit/secrets.toml.example`을 복사해 `.streamlit/secrets.toml`을 만들고 키를 넣습니다.
3. 다시 실행하면 결과 화면에 "AI가 고민을 읽고 추천했어요"가 표시됩니다.

`secrets.toml`은 `.gitignore`에 들어 있어 깃허브에 올라가지 않습니다. 키를 코드에 직접 쓰지 마세요.

## 배포 (Streamlit Community Cloud)

1. https://share.streamlit.io 에 GitHub 계정으로 로그인합니다.
2. 이 저장소와 브랜치, `app.py`를 선택해 배포합니다.
3. 앱 설정의 Secrets에 `GEMINI_API_KEY = "..."`를 붙여 넣습니다.

배포 서버는 재시작하면 `applications.csv`가 초기화될 수 있습니다. 시연용으로만 사용하세요.

## 팀이 채워야 할 것

- `data/mentors.json`의 M01, M02를 실제 선배 정보(가명)로 바꾸기. `_note` 줄은 지워도 됩니다.
- `matching.py`의 `CRISIS_KEYWORDS`(위기 표현 목록) 검토하기.

## 확인용 주소

- 신청 목록: 주소 뒤에 `?admin=1`을 붙이면 저장된 신청 기록을 볼 수 있습니다. (예: http://localhost:8501/?admin=1)
