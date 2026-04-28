# Week 5 Report — 테스트 작성 및 검증

**기간:** 2026-04-28  
**목표:** 전체 API에 대한 자동화 테스트 작성, 버그 발견 및 수정, 61개 테스트 전체 통과

---

## 테스트 결과 요약

```
Ran 61 tests in 35.8s

OK (errors=0, failures=0)
System check identified no issues (0 silenced).
```

| 앱 | 테스트 클래스 | 테스트 수 | 결과 |
|---|---|---|---|
| users | RegisterTest, LoginTest, MeTest, TokenRefreshTest, KakaoLoginTest | 16개 | 전체 통과 |
| products | ProductListTest, ProductCreateTest, ProductDetailTest, ProductStatusTest, MyProductListTest | 20개 | 전체 통과 |
| orders | OrderCreateTest, MyOrderListTest | 10개 | 전체 통과 |
| payments | CheckoutPageTest, PaymentVerifyTest, PaymentCancelTest | 15개 | 전체 통과 |
| **합계** | **13개 클래스** | **61개** | **전체 통과** |

---

## 테스트 환경

- **테스트 DB:** SQLite in-memory (`file:memorydb_default?mode=memory&cache=shared`)
- **테스트 클라이언트:** DRF `APITestCase`
- **외부 API Mock:** `unittest.mock.patch` (카카오 OAuth2, PortOne 결제/취소 API)
- **격리:** 테스트마다 독립적인 DB 상태 (setUp으로 픽스처 구성)

---

## 앱별 테스트 상세

### users — 16개

#### RegisterTest (5개)

| 테스트 | 검증 내용 | 예상 응답 |
|---|---|---|
| `test_success` | 정상 회원가입 → access/refresh/user 반환 | 201 |
| `test_duplicate_email` | 이미 존재하는 이메일 → 커스텀 에러 메시지 | 400 |
| `test_nickname_too_short` | 닉네임 1자 → 검증 실패 | 400 |
| `test_password_too_short` | 비밀번호 3자 → 검증 실패 | 400 |
| `test_missing_fields` | 이메일만 전송 → 필수 필드 누락 | 400 |

#### LoginTest (3개)

| 테스트 | 검증 내용 | 예상 응답 |
|---|---|---|
| `test_success` | 정상 로그인 → JWT 발급 | 200 |
| `test_wrong_password` | 비밀번호 불일치 | 401 |
| `test_wrong_email` | 존재하지 않는 이메일 | 401 |

#### MeTest (2개)

| 테스트 | 검증 내용 | 예상 응답 |
|---|---|---|
| `test_authenticated` | JWT 포함 요청 → 내 정보 반환 | 200 |
| `test_unauthenticated` | 토큰 없이 요청 | 401 |

#### TokenRefreshTest (2개)

| 테스트 | 검증 내용 | 예상 응답 |
|---|---|---|
| `test_refresh_success` | 유효한 refresh 토큰으로 access 토큰 재발급 | 200 |
| `test_invalid_refresh_token` | 조작된 refresh 토큰 | 401 |

#### KakaoLoginTest (4개)

| 테스트 | 검증 내용 | 예상 응답 |
|---|---|---|
| `test_missing_code` | code 없이 요청 | 400 |
| `test_new_user_signup` | 신규 카카오 유저 → DB 생성 + provider=kakao | 200 |
| `test_existing_local_user_provider_updated` | 동일 이메일 로컬 계정 → provider가 kakao로 업데이트 | 200 |
| `test_kakao_api_error` | 카카오 API HTTPError → 502 반환 | 502 |

> 카카오/PortOne 등 외부 API는 `@patch`로 모킹해 네트워크 없이 테스트한다.

---

### products — 20개

#### ProductListTest (4개)

| 테스트 | 검증 내용 |
|---|---|
| `test_list_no_auth` | 인증 없이 목록 조회 가능 (2개 반환) |
| `test_keyword_filter` | `?q=맥북` → 제목에 '맥북' 포함된 상품만 반환 |
| `test_category_filter` | `?category=fashion` → 해당 카테고리만 반환 |
| `test_status_filter` | `?status=sold` → 판매완료 상품만 반환 |

#### ProductCreateTest (5개)

| 테스트 | 검증 내용 |
|---|---|
| `test_create_success` | 정상 등록 → 201, status=on_sale |
| `test_create_unauthenticated` | 토큰 없이 등록 시도 → 401 |
| `test_price_too_low` | 가격 50원 → 400, "100원 이상" 메시지 |
| `test_price_too_high` | 가격 2억원 → 400 |
| `test_title_too_short` | 제목 1자 → 400 |

#### ProductDetailTest (6개)

| 테스트 | 검증 내용 |
|---|---|
| `test_retrieve_no_auth` | 인증 없이 상세 조회 가능 |
| `test_update_by_owner` | 본인 상품 수정 → 200 |
| `test_update_by_non_owner` | 타인 상품 수정 → **403** |
| `test_delete_by_owner` | 본인 상품 삭제 → 204, DB에서 제거 확인 |
| `test_delete_by_non_owner` | 타인 상품 삭제 → **403** |
| `test_retrieve_not_found` | 없는 상품 ID → 404 |

#### ProductStatusTest (3개)

| 테스트 | 검증 내용 |
|---|---|
| `test_status_change_by_owner` | 본인 상품 상태 변경 → 200, DB 반영 확인 |
| `test_status_change_by_non_owner` | 타인 상품 상태 변경 → **404** (존재 자체를 숨김) |
| `test_status_change_unauthenticated` | 토큰 없이 → 401 |

#### MyProductListTest (2개)

| 테스트 | 검증 내용 |
|---|---|
| `test_only_my_products_returned` | 본인 상품 2개만 반환, 타인 상품 미포함 확인 |
| `test_unauthenticated` | 토큰 없이 → 401 |

---

### orders — 10개

#### OrderCreateTest (7개)

| 테스트 | 검증 내용 |
|---|---|
| `test_create_success` | 정상 주문 → 201, status=pending, merchant_uid 포함 |
| `test_product_status_changes_to_reserved` | 주문 후 상품 status가 on_sale → reserved로 자동 변경 |
| `test_order_not_on_sale_product` | 판매완료 상품 주문 → 400, "판매중인 상품이 아닙니다" |
| `test_order_reserved_product` | 예약중 상품 주문 → 400 |
| `test_order_nonexistent_product` | 없는 상품 ID → 400 |
| `test_unauthenticated` | 토큰 없이 → 401 |
| `test_merchant_uid_is_unique` | 두 번 주문 시 merchant_uid가 서로 다름 |

#### MyOrderListTest (3개)

| 테스트 | 검증 내용 |
|---|---|
| `test_returns_only_my_orders` | buyer1의 주문 2개만 반환 |
| `test_other_buyer_sees_own_orders` | buyer2는 본인 주문 1개만 반환 |
| `test_unauthenticated` | 토큰 없이 → 401 |

---

### payments — 15개

#### CheckoutPageTest (1개)

| 테스트 | 검증 내용 |
|---|---|
| `test_checkout_page_returns_200` | GET 요청 → 200, HTML에 'PortOne', 'IMP.request_pay' 포함 |

#### PaymentVerifyTest (8개)

| 테스트 | 검증 내용 |
|---|---|
| `test_missing_params` | imp_uid/merchant_uid 없이 요청 → 400 |
| `test_order_not_found` | 잘못된 merchant_uid → 404 |
| `test_verify_success` | 정상 검증 → 200, order=paid, product=sold, Payment 생성 확인 |
| `test_amount_mismatch` | PortOne 금액(1000) ≠ 주문 금액(10000) → **400 위변조 탐지** |
| `test_payment_status_not_paid` | PortOne status=ready → 400, "결제 상태 이상" |
| `test_already_paid_order` | 이미 paid 주문 재검증 → 400, "이미 결제 완료" |
| `test_unauthenticated` | 토큰 없이 → 401 |
| `test_portone_api_error` | PortOne API 예외 발생 → **502** |

#### PaymentCancelTest (6개)

| 테스트 | 검증 내용 |
|---|---|
| `test_order_not_found` | 없는 주문 취소 → 404 |
| `test_cannot_cancel_pending_order` | pending 주문은 취소 불가 → 404 |
| `test_cancel_success` | 정상 취소 → 200, order=cancelled, product=on_sale 복구, payment=cancelled |
| `test_portone_cancel_error` | PortOne 취소 API 예외 → 502 |
| `test_unauthenticated` | 토큰 없이 → 401 |
| `test_other_buyer_cannot_cancel` | 타인의 주문 취소 → **404** |

---

## Mock 전략

외부 API를 실제로 호출하면 테스트 환경에서 키가 필요하고 네트워크 비용이 발생한다. `unittest.mock.patch`로 외부 호출 지점을 가로채 원하는 응답을 주입했다.

```python
# 예시: PortOne 결제 검증 성공 케이스
@patch('payments.views.fetch_payment', return_value={'amount': 10000, 'status': 'paid'})
def test_verify_success(self, mock_fetch):
    ...

# 예시: 카카오 토큰 교환 + 유저 정보 조회 모킹
@patch('users.kakao._get_kakao_token', return_value='kakao_access_token')
@patch('users.kakao._get_kakao_user_info', return_value={...})
def test_new_user_signup(self, mock_info, mock_token):
    ...
```

모킹 위치는 **사용되는 곳**(`payments.views.fetch_payment`)을 기준으로 한다. 정의된 곳(`payments.portone.fetch_payment`)을 모킹하면 이미 import된 참조에 반영되지 않는다.

---

## 테스트 중 발견된 버그 및 수정 사항

### 버그 1: allauth auth backend의 username 필드 충돌

**발견 경위:** `test_wrong_email`, `test_wrong_password` 실행 시 에러 발생

```
django.core.exceptions.FieldError: Cannot resolve keyword 'username' into field.
Choices are: created_at, email, emailaddress, ...
```

**원인:** `settings.py`에 `allauth.account.auth_backends.AuthenticationBackend`가 등록되어 있었고, 이 backend는 인증 시 `username` 필드로 DB 조회를 시도한다. 커스텀 User 모델에는 `username` 필드가 없다.

**수정:** allauth backend를 `AUTHENTICATION_BACKENDS`에서 제거하고 `django.contrib.auth.backends.ModelBackend`만 유지했다. 카카오 소셜 로그인은 커스텀 뷰에서 직접 처리하므로 allauth backend가 불필요하다.

```python
# 수정 전
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',  # ← 제거
]

# 수정 후
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]
```

### 버그 2: allauth deprecated 설정 경고

**발견 경위:** 테스트 실행 시 `System check` 경고 3건 출력

```
WARNINGS:
?: settings.ACCOUNT_AUTHENTICATION_METHOD is deprecated
?: settings.ACCOUNT_EMAIL_REQUIRED is deprecated
?: settings.ACCOUNT_USERNAME_REQUIRED is deprecated
```

**수정:** 최신 allauth 설정 형식으로 교체

```python
# 수정 전 (deprecated)
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'

# 수정 후
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
```

---

## 테스트 설계 원칙

1. **Happy path + Edge case 함께 검증:** 성공 케이스뿐 아니라 인증 없음(401), 권한 없음(403/404), 잘못된 입력(400), 외부 API 오류(502)를 모두 커버한다.

2. **상태 변화는 DB를 직접 확인:** API 응답만 보는 게 아니라 `refresh_from_db()`로 실제 DB 값이 바뀌었는지 검증한다.

    ```python
    self.order.refresh_from_db()
    self.assertEqual(self.order.status, Order.Status.PAID)
    self.order.product.refresh_from_db()
    self.assertEqual(self.order.product.status, 'sold')
    ```

3. **데이터 격리:** 각 테스트 클래스의 `setUp`에서 필요한 데이터만 생성하고, 테스트 DB는 매 실행마다 초기화된다.

4. **권한 경계 명확히:** 타인의 자원에 접근할 때 응답 코드가 403인지 404인지 의도적으로 구분한다. 상품 상태 변경(`ProductStatusView`)은 `seller == request.user` 조건으로 조회하므로 타인 접근 시 404를 반환한다 (리소스 존재 자체를 노출하지 않음).

---

## 면접 준비 포인트

**"테스트를 어떻게 작성했나요?"**
→ DRF의 `APITestCase`를 사용해 HTTP 레벨에서 테스트했습니다. 외부 API(카카오, PortOne)는 `unittest.mock.patch`로 모킹해 네트워크 의존성을 제거했습니다. 성공 케이스 외에 401/403/404/400/502 등 경계 조건을 모두 커버했고, API 응답뿐 아니라 `refresh_from_db()`로 DB 상태 변화를 직접 검증했습니다.

**"테스트 중 버그를 발견한 적 있나요?"**
→ 있습니다. `allauth`의 auth backend가 커스텀 User 모델에 없는 `username` 필드로 조회를 시도해 `FieldError`가 발생했습니다. 로그인 실패 케이스(`test_wrong_email`, `test_wrong_password`)를 작성하지 않았다면 운영 환경에서 존재하지 않는 이메일로 로그인 시도 시 500 에러가 발생할 수 있었습니다. 테스트가 실제 버그를 잡아낸 사례였습니다.
