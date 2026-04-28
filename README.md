# SecondDeal — Django 미니 중고마켓

백엔드 개발 직군 지원에 필요한 실무 경험을 직접 체험하기 위해 만든 토이 프로젝트입니다.

---

## 프로젝트 배경

아래 6가지 백엔드 역량을 요구하는 포지션에 지원하면서, 각 항목을 실제로 구현해본 경험을 쌓기 위해 시작했습니다.

| # | 요구 역량 | 이 프로젝트에서 구현한 내용 |
|---|---|---|
| 1 | 도메인 / 서버 이전 경험 | EC2 인스턴스 간 `mysqldump` + Nginx 트래픽 전환으로 서버 이전 실습 |
| 2 | 소셜 로그인 개발 | Kakao OAuth2 인가코드 플로우 직접 구현 + JWT 발급 |
| 3 | MySQL 기반 DB 설계 | users / products / orders / payments 테이블 ERD 직접 설계 |
| 4 | Django 프레임워크 | Django 5.2 + Django REST Framework로 전체 서버 구성 |
| 5 | 서비스 API 개발 | 인증·상품 CRUD·주문·결제 RESTful API 구현 |
| 6 | 결제 기능 연동 | PortOne(아임포트) 결제창 연동 + 서버 사이드 금액 검증 |

---

## 기술 스택

- **Backend:** Python 3.10, Django 5.2, Django REST Framework
- **Auth:** JWT (djangorestframework-simplejwt), Kakao OAuth2 (django-allauth)
- **DB:** MySQL (운영) / SQLite (로컬 개발)
- **결제:** PortOne (아임포트)
- **배포:** AWS EC2, Nginx, Gunicorn

---

## 시스템 아키텍처

```
[클라이언트]
     │
     │ HTTP
     ▼
┌──────────────┐
│    Nginx     │  ← 80/443, 정적 파일 직접 서빙, Slowloris 방어
└──────┬───────┘
       │ proxy_pass
       ▼
┌──────────────┐
│  Gunicorn    │  ← workers=3, 127.0.0.1:8000
│ (Django App) │
└──────┬───────┘
       │
  ┌────┴─────┐
  │          │
  ▼          ▼
MySQL      외부 API
(DB)    ├── 카카오 OAuth2
        └── PortOne 결제

[서버 이전]
인스턴스 A ──mysqldump──▶ 인스턴스 B
                              │
                          nginx reload
                          (무중단 전환)
```

---

## DB 설계 (ERD)

```
users ──────────────────────────────────────────────────┐
  id, email(unique), nickname, provider(local|kakao),   │
  profile_image, is_active, created_at                  │
                                                        │ FK seller
                                    ┌───────────────────▼────┐
                                    │        products        │
                                    │  id, title, price,     │
                                    │  category, status      │
                                    │  (on_sale|reserved|sold)│
                                    └──────────┬─────────────┘
                                               │ FK product
users                                          │
  │ FK buyer                       ┌───────────▼────┐
  └───────────────────────────────▶│    orders      │
                                   │  id, status    │
                                   │  (pending|paid │
                                   │  |cancelled)   │
                                   │  merchant_uid  │
                                   └───────┬────────┘
                                           │ OneToOne
                                  ┌────────▼───────┐
                                  │   payments     │
                                  │  imp_uid,      │
                                  │  amount,status │
                                  │  paid_at       │
                                  └────────────────┘
```

---

## 카카오 소셜 로그인 플로우

```
프론트  ──1. 카카오 로그인 버튼──▶  카카오 인증 서버
                                        │
                               2. 인가코드 발급
                                        │
프론트  ◀────────────────────────────────┘
  │
  │ 3. POST /api/auth/kakao/ { "code": "..." }
  ▼
백엔드
  │ 4. 카카오 토큰 서버에 code 교환 → access_token
  │ 5. 카카오 API로 유저 정보 조회
  │ 6. users 테이블 upsert
  │ 7. JWT 발급
  ▼
프론트  ◀── { access, refresh, user }
```

---

## 결제 위변조 방지 플로우

```
프론트         PortOne SDK          백엔드            PortOne API
  │                │                  │                   │
  │ 결제창 호출     │                  │                   │
  ├──────────────▶ │                  │                   │
  │                │ 결제 승인         │                   │
  │ ◀─ imp_uid ─── │                  │                   │
  │                                   │                   │
  │ POST /payments/verify/            │                   │
  │ { imp_uid, merchant_uid }         │                   │
  ├──────────────────────────────────▶│                   │
  │                                   │ imp_uid로 직접 조회│
  │                                   ├──────────────────▶│
  │                                   │ ◀── 실제 승인 금액 │
  │                                   │                   │
  │                                   │ DB 금액 vs 실제 금액 비교
  │                                   │ 불일치 → 400 에러
  │                                   │ 일치 → 주문 paid 처리
  │ ◀── 결제 완료 ────────────────────│
```

---

## API 목록

### 인증
```
POST /api/auth/register/        회원가입 (JWT 발급)
POST /api/auth/login/           로그인 (JWT 발급)
POST /api/auth/token/refresh/   액세스 토큰 갱신
GET  /api/auth/me/              내 정보 조회
POST /api/auth/kakao/           카카오 소셜 로그인
```

### 상품
```
GET    /api/products/                목록 조회 (?q=키워드&category=electronics&status=on_sale)
POST   /api/products/                상품 등록
GET    /api/products/<id>/           상품 상세
PUT    /api/products/<id>/           상품 수정 (본인만)
DELETE /api/products/<id>/           상품 삭제 (본인만)
PATCH  /api/products/<id>/status/    상태 변경 (본인만)
GET    /api/products/mine/           내 상품 목록
```

### 주문·결제
```
POST /api/orders/               주문 생성 (즉시 구매)
GET  /api/orders/mine/          구매 내역
GET  /api/payments/checkout/    결제창 HTML 페이지
POST /api/payments/verify/      결제 금액 검증 (위변조 방지)
POST /api/payments/cancel/      결제 취소
```

---

## 로컬 실행

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # SECRET_KEY 등 설정 후 저장
python manage.py migrate
python manage.py runserver
```

> MySQL로 전환하려면 `.env`에 `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` 추가

## EC2 배포

```bash
# 인스턴스 접속 후
bash deploy/deploy.sh

# 서버 이전 (A → B)
bash deploy/migrate_db.sh <B_IP> <B_PEM>
```

---

## 테스트 (Week 5)

전체 API에 대한 자동화 테스트를 작성하고 **61개 테스트 전체 통과**를 확인했다.  
상세 내용: [`report/week5.md`](report/week5.md)

| 앱 | 테스트 클래스 | 테스트 수 |
|---|---|---|
| users | RegisterTest, LoginTest, MeTest, TokenRefreshTest, KakaoLoginTest | 16개 |
| products | ProductListTest, ProductCreateTest, ProductDetailTest, ProductStatusTest, MyProductListTest | 20개 |
| orders | OrderCreateTest, MyOrderListTest | 10개 |
| payments | CheckoutPageTest, PaymentVerifyTest, PaymentCancelTest | 15개 |

- 외부 API(카카오 OAuth2, PortOne)는 `unittest.mock.patch`로 모킹해 네트워크 없이 테스트
- 성공 케이스 외 401 / 403 / 404 / 400 / 502 등 경계 조건 전부 커버
- `refresh_from_db()`로 DB 상태 변화(주문 상태, 상품 상태)를 직접 검증
- 테스트 과정에서 allauth backend의 `username` 필드 충돌 버그를 발견·수정 (미발견 시 운영 환경 500 에러 유발 가능)

---

## 보안 (Week 6)

7가지 취약점을 분석·보완하고 보안 테스트 6개를 추가해 **67개 전체 통과**를 확인했다.  
상세 내용: [`report/week6.md`](report/week6.md)

| 분류 | 취약점 | 보완 |
|---|---|---|
| 정보 노출 | 결제 오류·금액 상세가 응답에 포함 | 서버 로그만 기록, 클라이언트에 제네릭 메시지 반환 |
| 정보 노출 | 500 에러 내부 스택 노출 가능 | 커스텀 예외 핸들러 fallback 추가 |
| 인증 | 로그인 브루트포스 무제한 허용 | `ScopedRateThrottle` 5회/분 적용 |
| 인증 | 약한 비밀번호 허용 | Django `AUTH_PASSWORD_VALIDATORS` 연동 (최소 8자, 흔한 비밀번호·숫자전용 차단) |
| 파일 업로드 | 확장자·크기 미검증 | 확장자 화이트리스트(jpg/png/webp) + 5MB 제한 공통 유틸리티 |
| 설정 | 기본 `SECRET_KEY`로 운영 기동 허용 | 기동 시 `sys.exit()` 가드 추가 |
| 설정 | HTTPS·보안 헤더 미설정 | 운영 환경 조건부 HSTS·SSL redirect·보안 쿠키 설정 |

---

## 진행 상황

- [x] 1주차: Django 세팅, DB 설계, 인증·상품 CRUD API
- [x] 2주차: 카카오 소셜 로그인, 주문·결제 연동 (PortOne 위변조 검증)
- [x] 3주차: EC2 배포 스크립트, Nginx·Gunicorn 구성, 서버 이전 스크립트
- [x] 4주차: 에러 핸들링 통일, 입력값 검증 보완, Postman 컬렉션, 전체 회고
- [x] 5주차: 전체 API 자동화 테스트 61개 작성 및 통과
- [x] 6주차: 보안 취약점 7건 분석·보완, 보안 테스트 6개 추가 (67개 전체 통과)
