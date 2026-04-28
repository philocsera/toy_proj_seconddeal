# Week 2 Report — 소셜 로그인 + 결제 연동

**기간:** 2026-04-28  
**목표:** 카카오 OAuth2 소셜 로그인, PortOne 결제창 연동, 주문·결제 검증 API 구현

---

## 완료 항목

| 항목 | 상태 |
|---|---|
| django-allauth 설치 및 settings 등록 | 완료 |
| orders 앱 — Order 모델, 주문 생성·조회 API | 완료 |
| payments 앱 — Payment 모델 | 완료 |
| 카카오 OAuth2 커스텀 뷰 (`POST /api/auth/kakao/`) | 완료 |
| PortOne 결제 검증 API (`POST /api/payments/verify/`) | 완료 |
| PortOne 결제 취소 API (`POST /api/payments/cancel/`) | 완료 |
| 결제 체크아웃 HTML 페이지 (`GET /api/payments/checkout/`) | 완료 |
| 주문 생성 시 상품 상태 자동 변경 (on_sale → reserved) | 완료 |
| 결제 완료 시 상품 상태 자동 변경 (reserved → sold) | 완료 |
| 결제 취소 시 상품 상태 복구 (sold → on_sale) | 완료 |

---

## 구현 상세

### 카카오 소셜 로그인 플로우

allauth의 세션 기반 뷰를 그대로 쓰지 않고, JWT 발급을 위한 **커스텀 뷰**를 직접 구현했다.

```
[프론트엔드]
  1. 카카오 로그인 버튼 클릭
  2. https://kauth.kakao.com/oauth/authorize?... 로 리다이렉트
  3. 사용자 카카오 로그인 → 인가코드 발급
  4. 인가코드를 우리 서버로 POST

[백엔드 - users/kakao.py]
  5. POST /api/auth/kakao/ { "code": "..." }
  6. 카카오 토큰 서버에 인가코드 교환 → 카카오 액세스 토큰 획득
  7. 카카오 API로 유저 정보 조회 (email, nickname)
  8. users 테이블에 upsert
  9. JWT 발급 후 응답
```

**같은 이메일 충돌 처리:** 이미 이메일로 가입된 계정이 있으면 `provider`를 `kakao`로 업데이트한다. 카카오 계정에 이메일 정보가 없는 경우 `kakao_{id}@kakao.local` 형태의 가상 이메일을 생성해 충돌을 회피한다.

```python
# users/kakao.py 핵심 로직
user, created = User.objects.get_or_create(
    email=info['email'],
    defaults={'nickname': info['nickname'], 'provider': User.Provider.KAKAO},
)
if not created and user.provider == User.Provider.LOCAL:
    user.provider = User.Provider.KAKAO
    user.save(update_fields=['provider'])
```

### 결제 위변조 방지 설계

```
[결제 흐름]
  1. 클라이언트가 주문 생성 → merchant_uid 발급
  2. PortOne SDK로 결제창 호출 (merchant_uid, 금액 포함)
  3. 결제 완료 → PortOne이 imp_uid 발급
  4. 클라이언트가 imp_uid + merchant_uid를 서버로 POST

[서버 검증 - payments/views.py]
  5. merchant_uid로 주문 조회 → DB에 저장된 금액 확인
  6. PortOne REST API에 imp_uid로 직접 조회 → 실제 승인 금액 확인
  7. DB 금액 ≠ 실제 승인 금액 → 400 에러 (위변조 탐지)
  8. 금액 일치 + status == 'paid' → 주문·결제 상태 업데이트
```

핵심은 **클라이언트가 보내는 금액을 절대 믿지 않는 것**이다. 클라이언트가 JS를 조작해 금액을 낮춰 결제해도, 서버가 PortOne에 직접 조회한 금액과 비교하므로 위변조를 막을 수 있다.

### 주문-상품 상태 연동

```
주문 생성  →  상품: on_sale → reserved (다른 사람이 구매 불가)
결제 완료  →  상품: reserved → sold
결제 취소  →  상품: sold → on_sale (재판매 가능)
```

### DB 추가 설계 (orders, payments)

```
orders
  id, buyer_id(FK→users), product_id(FK→products),
  status(pending|paid|cancelled), total_price, merchant_uid(unique), created_at

payments
  id, order_id(OneToOne→orders), imp_uid(unique), merchant_uid,
  amount, status(ready|paid|cancelled|failed), paid_at
```

`payments.order`를 `OneToOneField`로 설계한 이유: 하나의 주문에 하나의 결제만 존재하고, `payment.order`로 양방향 접근이 가능해 코드가 단순해진다.

---

## 실제 실행 결과

### 주문 생성 (`POST /api/orders/`)
```json
{
  "id": 1,
  "buyer_nickname": "테스터",
  "product_title": "맥북 프로 14인치",
  "status": "pending",
  "total_price": 1800000,
  "merchant_uid": "order_19d84aef567a47708fc4ca8dcd9b35d1"
}
```

### 구매 내역 (`GET /api/orders/mine/`)
- 주문 생성 직후 목록에 정상 노출 확인

### 결제 체크아웃 페이지
- `GET /api/payments/checkout/` → HTTP 200, PortOne SDK 로드 HTML 반환

---

## API 추가 목록

```
POST /api/auth/kakao/          카카오 소셜 로그인 (인가코드 → JWT)
POST /api/orders/              주문 생성 (즉시 구매)
GET  /api/orders/mine/         구매 내역 조회
GET  /api/payments/checkout/   결제창 HTML 페이지
POST /api/payments/verify/     결제 검증 (위변조 방지)
POST /api/payments/cancel/     결제 취소
```

---

## 어려웠던 점 & 배운 것

### 1. allauth vs 커스텀 OAuth2 뷰
`allauth`의 소셜 로그인은 세션 기반 리다이렉트 방식이라, JWT를 반환하는 API 서버에 그대로 쓰기 어렵다. `allauth`는 `INSTALLED_APPS`에 등록해 `SocialAccount` 모델과 카카오 앱 설정 관리에만 활용하고, 실제 로그인 플로우는 `requests` 라이브러리로 직접 구현했다.

### 2. 카카오 이메일 미제공 케이스
카카오 계정에 이메일을 등록하지 않았거나, 이메일 제공에 동의하지 않으면 `kakao_account.email`이 없다. 이를 무시하면 `IntegrityError`가 발생한다. `kakao_{id}@kakao.local` 형태의 가상 이메일로 처리했다.

### 3. 결제 취소 시 상품 상태 복구 필요성
결제 취소 후 상품 상태를 `sold → on_sale`로 되돌리지 않으면 해당 상품이 영원히 판매 불가 상태로 남는다. 주문 취소·결제 취소가 발생하는 모든 경로에서 상품 상태를 복구해야 한다.

### 4. merchant_uid의 uniqueness
PortOne은 같은 `merchant_uid`로 중복 결제를 허용하지 않는다. `uuid4().hex`로 생성하면 충돌 확률이 사실상 0이지만, DB에 `unique=True` 제약을 걸어 이중으로 보호한다.

---

## 실제 테스트를 위해 필요한 외부 설정

카카오와 PortOne은 외부 서비스이므로 아래 설정이 별도로 필요하다.

| 항목 | 방법 |
|---|---|
| 카카오 REST API 키 | [카카오 개발자 콘솔](https://developers.kakao.com) → 앱 생성 → 카카오 로그인 활성화 |
| 카카오 리다이렉트 URI 등록 | 개발자 콘솔 → 플랫폼 → Web → `http://localhost:8000/api/auth/kakao/callback/` |
| PortOne 가맹점 식별코드 | [PortOne 콘솔](https://portone.io) → 가입 → 테스트 PG 설정 |
| checkout.html IMP.init() | 발급받은 가맹점 식별코드로 교체 |

---

## 3주차 예정 작업

- EC2 t2.micro 인스턴스 생성 및 초기 세팅
- Nginx + Gunicorn 배포 구성 파일 작성
- MySQL 설치 및 DB 세팅, `.env` 프로덕션 설정
- 서버 이전: `mysqldump` → 인스턴스 B로 복원 → Nginx 트래픽 전환
