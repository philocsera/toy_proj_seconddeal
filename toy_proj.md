# 토이 프로젝트: Django 기반 미니 중고마켓 플랫폼

## 프로젝트 개요

**프로젝트명:** SecondDeal — 개인 간 중고 거래 플랫폼  
**목표:** plan.md의 백엔드 개발 요건 6가지를 하나의 프로젝트 안에서 체험  
**예상 기간:** 3~4주  
**기술 스택:** Django, DRF, MySQL, AWS EC2, Nginx, Gunicorn, PortOne(아임포트)

---

## 요건별 경험 매핑

| plan.md 항목 | 이 프로젝트에서 체험하는 방법 |
|---|---|
| 1. 도메인/서버 이전 | 로컬 → EC2(t2.micro) 배포 후, 다른 인스턴스로 DB 마이그레이션 |
| 2. 소셜 로그인 | django-allauth + Kakao OAuth2 |
| 3. MySQL 기반 DB 설계 | 사용자·상품·주문·결제 4개 핵심 테이블 ERD 직접 설계 |
| 4. Django 프레임워크 | Django 4.x + DRF로 전체 서버 구성 |
| 5. 서비스 API 개발 | 상품 CRUD, 주문, 검색 RESTful API |
| 6. 결제 기능 연동 | PortOne(아임포트) 웹훅 + 결제 검증 API |

---

## 기능 범위 (MVP)

### 인증
- 이메일/비밀번호 회원가입·로그인
- **카카오 소셜 로그인** (django-allauth)
- JWT 발급 (djangorestframework-simplejwt)

### 상품
- 상품 등록·수정·삭제 (이미지 1장 포함)
- 상품 목록 조회 (카테고리 필터, 키워드 검색)
- 상품 상세 조회

### 주문·결제
- 장바구니 없이 즉시 구매 (단건 주문)
- **PortOne 결제창** 연동 (카드 결제)
- 결제 완료 후 서버에서 금액 검증 (위변조 방지)
- 결제 취소 API

### 마이페이지
- 내 상품 목록
- 구매 내역 조회

---

## DB 설계 (MySQL)

```
users
  id, email, nickname, profile_image, provider(local|kakao), created_at

products
  id, seller_id(FK→users), title, description, price, category,
  status(판매중|예약중|판매완료), image_url, created_at, updated_at

orders
  id, buyer_id(FK→users), product_id(FK→products),
  status(pending|paid|cancelled), total_price, created_at

payments
  id, order_id(FK→orders), imp_uid, merchant_uid,
  amount, status(ready|paid|cancelled|failed), paid_at
```

---

## 단계별 진행 계획

### 1주차 — Django 세팅 + DB 설계 + 기본 API
- Django 프로젝트 생성, MySQL 연결 (mysqlclient)
- ERD 설계 후 모델 작성 및 마이그레이션
- 회원가입·로그인 API (JWT)
- 상품 CRUD API

### 2주차 — 소셜 로그인 + 결제 연동
- django-allauth 설치, Kakao 개발자 앱 등록
- 카카오 OAuth2 플로우 구현 (인가코드 → 토큰 → 유저 정보)
- PortOne 결제창 연동 (프론트: 단순 HTML 페이지)
- 결제 검증 API (`imp_uid`로 PortOne 서버에 금액 재확인)

### 3주차 — 서버 배포 + 서버 이전 체험
- **1차 배포:** EC2 인스턴스 A에 Nginx + Gunicorn + MySQL 설치·배포
- 도메인 연결 (freenom 무료 도메인 또는 Route 53)
- **서버 이전 실습:**
  - EC2 인스턴스 B 생성
  - `mysqldump`로 DB 스냅샷 추출 → B로 복원
  - 애플리케이션 코드 재배포
  - Nginx에서 트래픽 전환 (다운타임 최소화 과정 체험)

### 4주차 — 마무리·정리
- 에러 핸들링, 입력값 검증 보완
- Postman 컬렉션 정리 (API 문서화)
- README 작성 (아키텍처 다이어그램 포함)
- 회고: 각 단계에서 어려웠던 점 정리 → 면접 답변 소재화

---

## 디렉토리 구조 (권장)

```
seconddeal/
├── config/              # settings, urls, wsgi
├── users/               # 인증, 소셜 로그인
├── products/            # 상품 CRUD
├── orders/              # 주문
├── payments/            # 결제 연동
├── requirements.txt
└── .env                 # SECRET_KEY, DB 접속 정보, PortOne API KEY
```

---

## 핵심 학습 포인트

1. **소셜 로그인:** `allauth` 시그널로 카카오 유저를 `users` 테이블에 upsert하는 로직
2. **결제 위변조 방지:** 클라이언트가 보낸 금액을 믿지 않고, `imp_uid`로 PortOne API를 직접 호출해 서버에서 금액 재검증
3. **서버 이전:** `mysqldump` + `scp`를 이용한 데이터 이관, 환경변수 관리의 중요성 체감
4. **DB 설계:** `status` 필드 ENUM 설계, 소프트 딜리트 vs 하드 딜리트 결정 과정

---

## 참고 라이브러리

```
Django==4.2
djangorestframework
djangorestframework-simplejwt
django-allauth
mysqlclient
python-dotenv
requests          # PortOne REST API 호출용
Pillow            # 이미지 처리
```
