# Week 3 Report — 서버 배포 + 서버 이전

**기간:** 2026-04-28  
**목표:** EC2 배포 구성 작성, MySQL 세팅, Nginx+Gunicorn 구성, 서버 이전 스크립트 작성

---

## 완료 항목

| 항목 | 상태 |
|---|---|
| Nginx 설정 파일 (`deploy/nginx.conf`) | 완료 |
| Gunicorn systemd 서비스 파일 (`deploy/gunicorn.service`) | 완료 |
| EC2 초기 배포 스크립트 (`deploy/deploy.sh`) | 완료 |
| MySQL 초기 세팅 SQL (`deploy/mysql_setup.sql`) | 완료 |
| 서버 이전 스크립트 (`deploy/migrate_db.sh`) | 완료 |
| settings.py MySQL 전환 분기 (`.env` 기반) | 1주차 완료 |

---

## 배포 아키텍처

```
인터넷
  │
  ▼
[EC2 인스턴스]
  │
  ├── Nginx (80/443 포트)
  │     ├── /static/  → staticfiles/ 직접 서빙
  │     ├── /media/   → media/ 직접 서빙
  │     └── /        → proxy_pass → 127.0.0.1:8000
  │
  └── Gunicorn (127.0.0.1:8000, workers=3)
        └── Django App
              └── MySQL (localhost:3306)
```

---

## EC2 초기 배포 절차

```bash
# 1. EC2 인스턴스 생성 후 SSH 접속
ssh -i key.pem ubuntu@<EC2_IP>

# 2. 배포 스크립트 실행
git clone https://github.com/philocsera/toy_proj_seconddeal.git seconddeal
bash seconddeal/deploy/deploy.sh

# 3. MySQL DB 생성
sudo mysql < seconddeal/deploy/mysql_setup.sql

# 4. .env 업로드 (로컬에서)
scp -i key.pem .env ubuntu@<EC2_IP>:~/seconddeal/.env

# 5. Gunicorn 재시작
sudo systemctl restart seconddeal
```

---

## 서버 이전 절차 (인스턴스 A → B)

### 전체 흐름

```
[인스턴스 A]                      [인스턴스 B]
mysqldump seconddeal.sql
     │
     └── scp ──────────────────────▶ /tmp/seconddeal.sql
                                         │
                                    mysql 복원
                                         │
                                    git clone + migrate
                                         │
[인스턴스 A]                             │
Nginx upstream 변경                      │
A:8000 → B:8000                         │
     │                                   │
     └──────────── 트래픽 전환 ──────────▶
```

### 실행 방법
```bash
# 인스턴스 A에서 실행
bash deploy/migrate_db.sh <B_IP> <B_PEM_PATH>
```

### 다운타임 최소화 원리
`nginx -t && systemctl reload nginx`는 Nginx를 재시작하지 않고 설정만 리로드한다. 기존 커넥션을 유지한 채 새 커넥션부터 B로 라우팅하므로 다운타임이 사실상 0이다.

---

## 핵심 설계 결정

### Gunicorn workers 수
CPU 코어 수 × 2 + 1을 권장한다. t2.micro는 vCPU 1개이므로 `workers=3`. 단, 메모리가 1GB뿐이라 워커가 많으면 OOM이 발생할 수 있어 3이 상한선이다.

### 정적 파일 Nginx 직접 서빙
Django의 `runserver`는 정적 파일을 서빙하지만 프로덕션에서는 Gunicorn이 정적 파일을 처리하지 않는다. `collectstatic`으로 `staticfiles/`에 모으고 Nginx가 직접 서빙하면 Django 프로세스 부하가 줄어든다.

### .env 파일 관리
`.env`는 `.gitignore`에 포함되어 저장소에 올라가지 않는다. 배포 시 `scp`로 직접 전송하거나, 프로덕션에서는 AWS Secrets Manager / Parameter Store를 사용한다.

### mysqldump 타이밍
서비스 중 덤프 시 일관성을 보장하려면 `--single-transaction` 옵션을 사용한다 (InnoDB 전용). 테이블 잠금 없이 트랜잭션 시작 시점의 스냅샷을 뜬다.

```bash
mysqldump --single-transaction -u root -p seconddeal > dump.sql
```

---

## 어려웠던 점 & 배운 것

### 1. Nginx와 Gunicorn의 역할 분리
처음에는 "왜 Gunicorn 앞에 Nginx를 두는가?"가 불명확했다. Nginx가 처리하는 것: 정적 파일 서빙, SSL 종단, 클라이언트 커넥션 관리, 요청 버퍼링. Gunicorn이 처리하는 것: Python WSGI 앱 실행. 슬로 클라이언트 공격(Slowloris)을 Nginx가 앞단에서 막아준다는 점이 핵심이었다.

### 2. 서버 이전 시 환경변수 누락
코드는 배포됐는데 `.env`가 없어 서버가 뜨지 않는 상황이 가장 흔한 실수다. 배포 스크립트에서 `.env` 존재 여부를 먼저 체크하도록 구성했다.

### 3. DB 이전 vs 코드 이전 순서
코드를 먼저 배포하면 `migrate`가 실행되어 스키마가 바뀐 뒤 덤프를 복원하면 불일치가 생긴다. 올바른 순서: DB 덤프 → B에 복원 → 코드 배포 → migrate.

### 4. MySQL utf8 vs utf8mb4
MySQL의 `utf8`은 3바이트 한계라 이모지를 저장하면 에러가 난다. `utf8mb4`를 써야 한다. `mysql_setup.sql`과 `settings.py`의 `OPTIONS: {'charset': 'utf8mb4'}`로 통일했다.

---

## 4주차 예정 작업

- 에러 핸들링 통일 (커스텀 exception handler)
- 입력값 검증 보완 (가격 범위, 닉네임 길이 등)
- Postman 컬렉션 JSON 작성
- README 아키텍처 다이어그램 업데이트
- 전체 회고 정리
