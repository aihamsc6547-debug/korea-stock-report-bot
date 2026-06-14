# Operations

## 첫 실행 순서

```bash
cd /Users/miniagent/Documents/Codex/2026-05-01/https-chatgpt-com-share-69f33e1f-266c/stock-report-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env`에 네이버 API 키를 입력한다.

```text
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
```

실행:

```bash
python -m app.main --date 20260501
```

## 리포트 저장 위치

```text
Obsidian-Archive/Market-Reports/YYYY/MM/YYYY-MM-DD-korea-market-report.md
```

## 자동 실행 권장 시간

- 16:10: 빠른 리포트
- 16:30: 데이터 반영 지연을 고려한 안정적 리포트

초기 운영은 16:30을 권장한다.

## macOS cron 예시

```cron
30 16 * * 1-5 cd /Users/miniagent/Documents/Codex/2026-05-01/https-chatgpt-com-share-69f33e1f-266c/stock-report-bot && . .venv/bin/activate && python -m app.main
```

## 운영 체크리스트

- [ ] `pykrx` 설치 확인
- [ ] 네이버 API 키 입력
- [ ] 하루치 리포트 수동 실행
- [ ] 리포트가 Obsidian에서 열리는지 확인
- [ ] 자동 실행 등록
- [ ] 1주일치 리포트 품질 점검

## 데이터 소스 메모

- 1차: `pykrx`를 통한 KRX 시세
- 2차: KRX 응답이 비어 있거나 막히면 Naver 모바일 증권 시세를 fallback으로 사용
- Naver fallback은 최신 장마감 데이터 기준으로 동작한다.

## 현재 선별 조건

- 상한가, 12% 이상 상승, 거래량 1,000만 주 이상 중 하나 이상 충족
- 동시에 당일 거래대금 50억 원 이상 충족
