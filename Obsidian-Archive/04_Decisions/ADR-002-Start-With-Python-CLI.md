# ADR-002: Start With Python CLI

## 상태

Accepted

## 배경

프로젝트의 핵심은 화면보다 매일 반복 가능한 데이터 수집, 필터링, 뉴스 요약, Obsidian 기록이다.

## 결정

초기 버전은 웹앱이나 Obsidian 플러그인이 아니라 Python CLI로 구현한다.

## 결과

- 빠르게 자동화할 수 있다.
- macOS `cron` 또는 `launchd`로 장마감 이후 실행할 수 있다.
- 결과물은 Obsidian Markdown 파일로 남기므로 UI가 없어도 바로 활용 가능하다.
- 이후 필요하면 웹 대시보드나 Obsidian 플러그인으로 확장할 수 있다.

