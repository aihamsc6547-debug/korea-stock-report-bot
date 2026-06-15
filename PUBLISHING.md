# Web Publishing Guide

이 프로젝트는 GitHub Actions와 GitHub Pages로 매일 장마감 리포트를 웹에 발행하도록 구성되어 있습니다.

## 구조

- `stock-report-bot/app/main.py`: 장마감 리포트 Markdown 생성
- `stock-report-bot/app/build_site.py`: Markdown 리포트를 정적 HTML 사이트로 변환
- `published-reports/`: 웹 공개용 Markdown 리포트 아카이브
- `public/`: 빌드된 HTML 출력 폴더
- `.github/workflows/daily-web-publish.yml`: 매일 자동 발행 workflow

## GitHub에서 해야 할 일

1. GitHub에 이 프로젝트를 저장소로 올립니다.
2. 저장소 `Settings > Secrets and variables > Actions`에서 아래 repository secret을 추가합니다.

```text
NAVER_CLIENT_ID
NAVER_CLIENT_SECRET
```

3. 저장소 `Settings > Pages`에서 Source를 `GitHub Actions`로 설정합니다.
4. `Actions` 탭에서 `Daily Korea Stock Web Report` workflow를 한 번 수동 실행합니다.

이후 평일 16:40 KST에 자동으로 리포트를 만들고 GitHub Pages에 배포합니다.
workflow의 cron 값은 GitHub 예약 실행 안정성을 위해 UTC 기준 `40 7 * * 1-5`로 적어두었습니다.

## 로컬에서 웹 사이트 미리보기

이미 생성된 Obsidian 리포트로 사이트를 빌드합니다.

```bash
cd stock-report-bot
python -m app.build_site
```

생성 위치:

```text
../public/index.html
```

특정 공개 폴더를 기준으로 빌드하려면:

```bash
python -m app.build_site --source-dir ../published-reports --output-dir ../public
```

## 운영 메모

- workflow는 `published-reports/`에 생성된 Markdown을 커밋하므로 날짜별 아카이브가 유지됩니다.
- `public/`은 배포용 산출물이라 저장소에 커밋하지 않습니다.
- 휴장일에는 프로그램이 최근 거래일 데이터를 찾아 사용합니다. 이미 같은 날짜 리포트가 있으면 커밋 변경 없이 Pages 배포만 다시 시도될 수 있습니다.
