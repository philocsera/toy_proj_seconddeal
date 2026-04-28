# SecondDeal — Django 미니 중고마켓

백엔드 개발 직군 지원에 필요한 실무 경험을 직접 체험하기 위해 만든 토이 프로젝트입니다.

---

## 프로젝트 배경

아래 6가지 백엔드 역량을 요구하는 포지션에 지원하면서, 각 항목을 실제로 구현해본 경험을 쌓기 위해 시작했습니다.

| # | 요구 역량 | 이 프로젝트에서 구현한 내용 |
|---|---|---|
| 1 | 도메인 / 서버 이전 경험 | EC2 인스턴스 간 `mysqldump` + Nginx 트래픽 전환으로 서버 이전 실습 |
| 2 | 소셜 로그인 개발 | `django-allauth` + Kakao OAuth2 인가코드 플로우 구현 |
| 3 | MySQL 기반 DB 설계 | users / products / orders / payments 테이블 ERD 직접 설계 |
| 4 | Django 프레임워크 | Django 4.2 + Django REST Framework로 전체 서버 구성 |
| 5 | 서비스 API 개발 | 인증·상품 CRUD·주문 RESTful API 구현 |
| 6 | 결제 기능 연동 | PortOne(아임포트) 결제창 연동 + 서버 사이드 금액 검증 |

---

## 기술 스택

- **Backend:** Python 3.10, Django 4.2, Django REST Framework
- **Auth:** JWT (djangorestframework-simplejwt), Kakao OAuth2 (django-allauth)
- **DB:** MySQL (운영) / SQLite (로컬 개발)
- **결제:** PortOne (아임포트)
- **배포:** AWS EC2, Nginx, Gunicorn

---

## 주요 기능

- 이메일 회원가입·로그인 / 카카오 소셜 로그인
- 상품 등록·수정·삭제·상태 관리 (판매중 / 예약중 / 판매완료)
- 카테고리·키워드 기반 상품 검색
- 단건 즉시 구매 + 카드 결제 (결제 위변조 서버 검증 포함)
- 구매 내역 및 내 상품 목록 조회

---

## API 목록

### 인증
```
POST /api/auth/register/        회원가입 (JWT 발급)
POST /api/auth/login/           로그인 (JWT 발급)
POST /api/auth/token/refresh/   액세스 토큰 갱신
GET  /api/auth/me/              내 정보 조회
```

### 상품
```
GET    /api/products/                목록 조회 (카테고리·키워드 필터)
POST   /api/products/                상품 등록
GET    /api/products/<id>/           상품 상세
PUT    /api/products/<id>/           상품 수정 (본인만)
DELETE /api/products/<id>/           상품 삭제 (본인만)
PATCH  /api/products/<id>/status/    상태 변경 (본인만)
GET    /api/products/mine/           내 상품 목록
```

---

## 로컬 실행

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # SECRET_KEY 등 설정
python manage.py migrate
python manage.py runserver
```

> MySQL로 전환하려면 `.env`에 `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` 추가

---

## 진행 상황

- [x] 1주차: Django 세팅, DB 설계, 인증·상품 CRUD API
- [ ] 2주차: 카카오 소셜 로그인, PortOne 결제 연동
- [ ] 3주차: EC2 배포, 서버 이전 실습
- [ ] 4주차: 에러 핸들링 보완, API 문서화, 회고 정리
