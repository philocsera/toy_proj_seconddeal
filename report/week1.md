# Week 1 Report — Django 세팅 + DB 설계 + 기본 API

**기간:** 2026-04-28  
**목표:** Django 프로젝트 초기 세팅, MySQL 호환 DB 설계, 회원가입·로그인 API, 상품 CRUD API 구현

---

## 완료 항목

| 항목 | 상태 |
|---|---|
| Django 4.2 프로젝트 생성 및 앱 분리 (users, products) | 완료 |
| .env 기반 설정 분리 (python-dotenv) | 완료 |
| 커스텀 User 모델 (AbstractBaseUser) | 완료 |
| Product 모델 (TextChoices ENUM 적용) | 완료 |
| DB 마이그레이션 (SQLite 로컬, MySQL 전환 준비) | 완료 |
| 회원가입 API `POST /api/auth/register/` | 완료 |
| 로그인 API `POST /api/auth/login/` + JWT 발급 | 완료 |
| 토큰 갱신 API `POST /api/auth/token/refresh/` | 완료 |
| 내 정보 조회 API `GET /api/auth/me/` | 완료 |
| 상품 등록 API `POST /api/products/` | 완료 |
| 상품 목록 조회 API `GET /api/products/` (카테고리·키워드 필터) | 완료 |
| 상품 상세 조회 `GET /api/products/<id>/` | 완료 |
| 상품 수정·삭제 `PUT/DELETE /api/products/<id>/` (본인만) | 완료 |
| 상품 상태 변경 `PATCH /api/products/<id>/status/` | 완료 |
| 내 상품 목록 `GET /api/products/mine/` | 완료 |
| Django Admin 등록 (User, Product) | 완료 |

---

## 구현 상세

### 프로젝트 구조

```
0428/
├── config/          # settings.py, urls.py, wsgi.py
├── users/           # User 모델, 인증 API
├── products/        # Product 모델, CRUD API
├── report/          # 주차별 회고
├── .env             # 환경변수 (SECRET_KEY, DB 설정)
├── requirements.txt
└── manage.py
```

### DB 설계 결정 사항

**AbstractBaseUser를 사용한 이유**  
Django 기본 `User` 모델은 `username` 필드가 필수다. 이 프로젝트는 `email`을 로그인 식별자로 쓰므로, `USERNAME_FIELD = 'email'`로 설정하기 위해 `AbstractBaseUser`를 직접 구현했다. 2주차 카카오 소셜 로그인 시 `provider` 컬럼을 그대로 활용할 수 있다.

**TextChoices ENUM 적용**  
`Product.status` (on_sale / reserved / sold), `Product.category` (electronics / fashion / book / sports / etc)를 Django `TextChoices`로 정의했다. DB에는 문자열로 저장되어 MySQL 마이그레이션 시에도 `ALTER TABLE` 없이 값 추가가 가능하다. (MySQL `ENUM` 타입은 값 추가 시 잠금이 발생하는 단점이 있어 의도적으로 `VARCHAR`+`TextChoices` 패턴을 선택했다.)

**SQLite → MySQL 전환 전략**  
로컬은 MySQL 설치 없이 SQLite로 개발하고, `.env`에 `DB_ENGINE` 변수 존재 여부로 DB를 분기한다. 3주차 EC2 배포 시 `.env`에 MySQL 접속 정보를 추가하면 코드 변경 없이 전환된다.

```python
# config/settings.py 핵심 분기
if os.getenv('DB_ENGINE'):
    DATABASES = { 'default': { 'ENGINE': os.getenv('DB_ENGINE'), ... } }
else:
    DATABASES = { 'default': { 'ENGINE': 'django.db.backends.sqlite3', ... } }
```

### 인증 구조

JWT를 `djangorestframework-simplejwt`로 발급한다. Access Token 유효시간 2시간, Refresh Token 7일. 회원가입·로그인 응답에 `{ access, refresh, user }` 형태로 통일하여 프론트에서 별도 `/me` 호출 없이 사용자 정보를 바로 쓸 수 있도록 설계했다.

```
POST /api/auth/register/   → 201, { access, refresh, user }
POST /api/auth/login/      → 200, { access, refresh, user }
POST /api/auth/token/refresh/ → 200, { access }
GET  /api/auth/me/         → 200, user 객체
```

### 상품 API 설계

- 목록 조회는 인증 없이 가능 (`IsAuthenticatedOrReadOnly`)
- 등록·수정·삭제는 JWT 필요
- 수정·삭제는 `seller == request.user` 검증 후 `PermissionDenied` 처리
- 상태 변경은 별도 `PATCH /products/<id>/status/`로 분리 → 클라이언트가 가격·설명 변경과 상태 변경을 명확히 구분

```
GET    /api/products/             → 목록 (인증 불필요)
GET    /api/products/?q=맥북      → 키워드 검색
GET    /api/products/?category=electronics → 카테고리 필터
POST   /api/products/             → 등록 (JWT 필요)
GET    /api/products/<id>/        → 상세
PUT    /api/products/<id>/        → 수정 (본인만)
DELETE /api/products/<id>/        → 삭제 (본인만)
PATCH  /api/products/<id>/status/ → 상태 변경 (본인만)
GET    /api/products/mine/        → 내 상품 목록
```

---

## 실제 실행 결과

### 회원가입 (`POST /api/auth/register/`)
```json
{
  "access": "eyJhbGci...",
  "refresh": "eyJhbGci...",
  "user": {
    "id": 1,
    "email": "test@example.com",
    "nickname": "테스터",
    "provider": "local",
    "created_at": "2026-04-28T20:40:11+09:00"
  }
}
```

### 상품 등록 (`POST /api/products/`)
```json
{
  "id": 1,
  "seller_nickname": "테스터",
  "title": "맥북 프로 14인치",
  "price": 1800000,
  "category": "electronics",
  "status": "on_sale"
}
```

### 상태 변경 (`PATCH /api/products/1/status/`)
```json
{ "status": "reserved" }  →  응답: "상태: reserved"
```

모든 엔드포인트 HTTP 상태코드 정상 (201 Created, 200 OK, 401/403 권한 오류).

---

## 어려웠던 점 & 배운 것

### 1. AbstractBaseUser 구현 시 `UserManager` 필수
`AbstractBaseUser`를 쓰면 `create_superuser`도 직접 구현해야 한다. `is_staff`, `is_superuser`를 `extra`로 받지 않으면 `python manage.py createsuperuser`가 동작하지 않는다.

### 2. `AUTH_USER_MODEL` 선언 타이밍
`settings.py`에 `AUTH_USER_MODEL = 'users.User'`를 먼저 선언하지 않으면, `products.Product`의 `seller = ForeignKey(settings.AUTH_USER_MODEL, ...)` 참조 시 마이그레이션 의존성 오류가 발생한다. 앱 등록 순서보다 이 설정이 선행되어야 한다.

### 3. MySQL `ENUM` vs `VARCHAR+TextChoices`
MySQL `ENUM` 타입은 값 추가 시 테이블 전체 잠금(Full Table Lock)이 발생하여 운영 중 변경이 위험하다. `VARCHAR(20)` + Django `TextChoices`로 처리하면 DB 마이그레이션 없이 Python 코드만 수정해 새 값을 추가할 수 있다.

### 4. 소셜 로그인 대비 `provider` 컬럼 설계
이메일 로그인과 카카오 로그인 모두 `users` 테이블 하나에 넣을 것이기 때문에, 2주차를 염두에 두고 `provider` 컬럼을 미리 추가했다. 같은 이메일로 두 경로 가입 시 충돌 방지 로직은 2주차에 `django-allauth` 시그널로 처리 예정.

---

## 2주차 예정 작업

- `django-allauth` 설치 및 카카오 OAuth2 앱 등록
- 카카오 인가코드 → 액세스 토큰 → 유저 정보 조회 플로우 구현
- `allauth` 시그널: 카카오 유저 `users` 테이블 upsert
- PortOne(아임포트) 가입 및 테스트 결제키 발급
- 결제 검증 API 설계 (`imp_uid` 기반 금액 재검증)
