# Korea Stock Report Bot

한국 주식시장 장마감 후 급등/거래량 종목을 선별하고, 관련 뉴스와 요약을 붙여 Obsidian용 Markdown 리포트를 생성하는 MVP입니다.

## 기능

- KOSPI/KOSDAQ 일별 시세 수집
- `pykrx` 실패 시 Naver 모바일 증권 시세 fallback
- 조건 필터링
  - 상한가 추정 종목
  - 당일 12% 이상 상승 종목
  - 당일 거래량 1,000만 주 이상 종목
  - 당일 거래대금 50억 원 이상 필수
- 네이버 뉴스 검색 API로 관련 기사 수집
- 뉴스 제목/요약 기반 부각 원인 추정
- Obsidian에서 바로 읽을 수 있는 Markdown 파일 생성

## 설치

```bash
cd stock-report-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env`에 네이버 개발자 센터에서 발급받은 값을 입력합니다.

```text
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
```

## 공유 주의

이 프로젝트를 다른 사람에게 공유할 때는 `.env`를 절대 포함하지 마세요. `.env`에는 네이버 API `Client ID`와 `Client Secret`이 들어갑니다.

공유 대상에는 `.env.example`만 포함하고, 받는 사람이 자기 네이버 API 키를 직접 넣어야 합니다.

## 실행

```bash
python -m app.main --date 20260501
```

날짜를 생략하면 오늘 날짜 기준으로 실행합니다.

```bash
python -m app.main
```

기본 출력 위치는 이 저장소의 Obsidian Vault입니다.

```text
../Obsidian-Archive/Market-Reports/YYYY/MM/YYYY-MM-DD-korea-market-report.md
```

## 장마감 자동 실행 예시

macOS `cron` 기준으로 평일 16:10에 실행하려면:

```cron
10 16 * * 1-5 cd /path/to/stock-report-bot && . .venv/bin/activate && python -m app.main
```

## 웹 발행

이미 생성된 Markdown 리포트를 정적 HTML 사이트로 변환하려면:

```bash
python -m app.build_site
```

기본 입력은 `../Obsidian-Archive/Market-Reports`, 기본 출력은 `../public`입니다.

GitHub Pages로 매일 자동 발행하려면 저장소에 포함된 `.github/workflows/daily-web-publish.yml`을 사용합니다.

필요한 GitHub repository secret:

```text
NAVER_CLIENT_ID
NAVER_CLIENT_SECRET
```

자세한 설정 순서는 `../PUBLISHING.md`를 참고하세요.

## 참고

- 시세 데이터는 `pykrx`를 우선 사용하고, KRX 응답이 막히거나 비어 있으면 Naver 모바일 증권 시세를 fallback으로 사용합니다.
- 뉴스 검색은 네이버 뉴스 검색 API를 사용합니다.
- 기사 전문을 크롤링하지 않고 검색 API의 제목/요약/링크를 활용합니다.
