# Sharing Guide

이 프로젝트를 다른 사람에게 공유할 때는 코드와 문서만 공유하고, 개인 API 키와 로컬 실행 환경은 제외해야 합니다.

## 절대 공유하지 말 것

- `stock-report-bot/.env`
- `stock-report-bot/.venv/`
- `stock-report-bot/.mplconfig/`
- `.pycache/`
- `.DS_Store`
- 개인용으로 생성한 일별 리포트 원본

`.env`에는 네이버 `Client ID`와 `Client Secret`이 들어갑니다. 이 값은 비밀번호처럼 취급해야 합니다.

## 공유해도 되는 것

- `stock-report-bot/app/`
- `stock-report-bot/tests/`
- `stock-report-bot/requirements.txt`
- `stock-report-bot/.env.example`
- `stock-report-bot/README.md`
- `Obsidian-Archive/01_Project/`
- `Obsidian-Archive/02_Design/`
- `Obsidian-Archive/03_Dev-Log/`
- `Obsidian-Archive/04_Decisions/`
- `Obsidian-Archive/Templates/`

## 가장 추천하는 방식: GitHub 저장소

1. GitHub에서 새 저장소를 만든다.
2. 이 프로젝트 폴더에서 아래 명령을 실행한다.

```bash
git init
git add .
git status
git commit -m "Initial Korea stock report bot"
git branch -M main
git remote add origin https://github.com/YOUR_NAME/YOUR_REPO.git
git push -u origin main
```

`git status` 단계에서 `.env`, `.venv`, `.mplconfig`, `.pycache`, `.DS_Store`, 생성된 일별 리포트가 올라가지 않는지 확인한다.

## zip 파일로 공유하기

GitHub를 쓰지 않고 zip으로 전달하려면 프로젝트 상위 폴더에서 아래처럼 만든다.

```bash
zip -r korea-stock-report-bot-share.zip \
  stock-report-bot \
  Obsidian-Archive \
  SHARING.md \
  .gitignore \
  -x "*/.env" \
  -x "*/.venv/*" \
  -x "*/.mplconfig/*" \
  -x "*/__pycache__/*" \
  -x ".pycache/*" \
  -x "*/.DS_Store" \
  -x "Obsidian-Archive/Market-Reports/20*/*/*.md"
```

받는 사람은 압축을 푼 뒤 `stock-report-bot/.env.example`을 복사해 자기 네이버 API 키를 입력해야 한다.

## 받는 사람이 실행하는 순서

```bash
cd stock-report-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env`에 본인의 네이버 API 키를 입력한다.

```text
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
```

실행:

```bash
python -m app.main
```

특정 날짜로 실행:

```bash
python -m app.main --date 20260501
```

## 공유할 때 설명하면 좋은 한 줄

한국 주식 장마감 후 급등, 상한가, 거래량 급증 종목을 선별하고 네이버 뉴스 검색 결과를 붙여 Obsidian용 Markdown 리포트를 생성하는 Python CLI 도구입니다.

