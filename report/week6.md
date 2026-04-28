# Week 6 보안 취약점 분석 및 보완 보고서

## 개요

Week 5에서 구현된 전체 기능에 대해 보안 취약점을 체계적으로 분석하고,  
발견된 문제를 코드 레벨에서 보완한 뒤 보안 테스트를 추가하여 검증했다.

---

## 1. 취약점 분석 결과

### 1-1. 정보 노출 (Information Disclosure)

| 위치 | 취약점 | 위험도 |
|------|--------|--------|
| `payments/views.py` | PortOne API 오류 메시지가 그대로 클라이언트에 반환됨 | 높음 |
| `payments/views.py` | 결제 금액 불일치 시 실제 주문/결제 금액이 응답에 포함됨 | 중간 |
| `config/exceptions.py` | 처리되지 않은 예외(500)의 내부 스택 정보 노출 가능 | 높음 |

**상세:** 결제 검증 실패 시 기존 코드는 `f'PortOne API 오류: {e}'`, `f'결제 금액 불일치 (주문: {order.total_price}, 실제: ...)'`처럼 내부 금액 정보와 외부 API 에러 메시지를 그대로 응답에 포함하고 있었다. 공격자가 이를 악용해 주문 금액 정보를 수집하거나 시스템 구조를 파악할 수 있다.

---

### 1-2. 인증·인가 취약점

| 위치 | 취약점 | 위험도 |
|------|--------|--------|
| `users/views.py` (LoginView) | 로그인 시도에 횟수 제한이 없어 브루트포스 공격 가능 | 높음 |
| `users/serializers.py` | `CharField(min_length=6)`만 적용, Django 비밀번호 정책 미적용 | 중간 |

**상세:** 로그인 엔드포인트에 Rate Limit이 없어 동일 IP에서 무제한으로 비밀번호를 시도할 수 있었다. 또한 회원가입 시 최소 길이(6)만 검사하고, 흔한 비밀번호나 숫자만으로 구성된 비밀번호를 허용하고 있었다.

---

### 1-3. 파일 업로드 보안

| 위치 | 취약점 | 위험도 |
|------|--------|--------|
| `products/serializers.py` | 업로드 파일 확장자·크기 검증 없음 | 높음 |
| `users/serializers.py` | 프로필 이미지 업로드 시 동일한 검증 부재 | 중간 |

**상세:** 이미지 업로드 필드에 확장자 화이트리스트나 파일 크기 제한이 없어, `.php` 등 실행 파일 업로드 시도나 수십 MB 파일로 서버 자원을 소모시키는 공격이 가능했다.

---

### 1-4. 설정 보안 (Configuration Security)

| 위치 | 취약점 | 위험도 |
|------|--------|--------|
| `config/settings.py` | `SECRET_KEY` 기본값으로 운영 환경 기동 허용 | 매우 높음 |
| `config/settings.py` | HTTPS 강제, 보안 헤더 미설정 | 중간 |
| `config/settings.py` | 파일 업로드 메모리 크기 제한 없음 | 낮음 |

---

## 2. 보완 내용

### 2-1. 정보 노출 차단

**`payments/views.py`**

```python
# Before (취약)
return Response({'detail': f'PortOne API 오류: {e}'}, status=502)
return Response({'detail': f'결제 금액 불일치 (주문: {order.total_price}, 실제: {paid_info["amount"]})'}, ...)

# After (보완)
logger.error('PortOne fetch_payment 오류 | imp_uid=%s | %s', imp_uid, e)
return Response({'detail': '결제 정보 조회 중 오류가 발생했습니다.'}, status=502)

logger.warning('결제 금액 불일치 | merchant_uid=%s | 주문=%s | 실제=%s', ...)
return Response({'detail': '결제 금액이 일치하지 않습니다.'}, ...)
```

내부 상세 정보는 서버 로그에만 기록하고, 클라이언트에는 일반적인 메시지만 반환한다.

**`config/exceptions.py`**

```python
# 처리되지 않은 예외(500) — 내부 정보를 클라이언트에 노출하지 않음
logger.exception('Unhandled exception in view: %s', exc)
response = Response(
    {'detail': '서버 오류가 발생했습니다.', 'status_code': 500},
    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
)
```

---

### 2-2. 로그인 Rate Limiting (브루트포스 방어)

**`config/settings.py`**

```python
'DEFAULT_THROTTLE_CLASSES': [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle',
],
'DEFAULT_THROTTLE_RATES': {
    'anon': '100/day',
    'user': '1000/day',
    'login': '5/min',   # 로그인 전용 스코프
},
```

**`users/views.py`**

```python
from rest_framework.throttling import ScopedRateThrottle

class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'  # 동일 IP에서 분당 5회 초과 시 429
```

---

### 2-3. 비밀번호 정책 강화

**`config/settings.py`**

```python
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
```

**`users/serializers.py`**

```python
def validate_password(self, value):
    try:
        validate_password(value)          # Django 정책 전체 적용
    except DjangoValidationError as e:
        raise serializers.ValidationError(e.messages)
    return value
```

---

### 2-4. 파일 업로드 보안 (중앙화된 검증 유틸리티)

**`config/validators.py`** (신규)

```python
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_IMAGE_SIZE_MB = 5
MAX_IMAGE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024

def validate_image_file(image):
    ext = os.path.splitext(image.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise serializers.ValidationError(
            f'지원하지 않는 파일 형식입니다. ({", ".join(ALLOWED_IMAGE_EXTENSIONS)})'
        )
    if image.size > MAX_IMAGE_BYTES:
        raise serializers.ValidationError(
            f'파일 크기는 {MAX_IMAGE_SIZE_MB}MB 이하여야 합니다.'
        )
    return image
```

`products/serializers.py`, `users/serializers.py`의 이미지 필드에서 동일 함수를 호출하도록 통합.

---

### 2-5. 설정 보안 강화

**`config/settings.py`**

```python
# SECRET_KEY 미설정 시 운영 환경 기동 차단
if not DEBUG and SECRET_KEY == 'dev-secret-key':
    sys.exit('운영 환경에서 SECRET_KEY를 반드시 설정해야 합니다.')

# 업로드 크기 제한 (5MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# 운영 환경 보안 헤더
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
```

---

## 3. 보안 테스트 추가

### 3-1. 비밀번호 정책 테스트 (`users/tests.py` - `PasswordPolicyTest`)

| 테스트 | 검증 내용 | 결과 |
|--------|-----------|------|
| `test_password_min_length_8` | 8자 미만 비밀번호 거부 | PASS |
| `test_numeric_only_password_rejected` | 숫자로만 구성된 비밀번호 거부 | PASS |

### 3-2. Rate Limit 테스트 (`users/tests.py` - `LoginRateLimitTest`)

| 테스트 | 검증 내용 | 결과 |
|--------|-----------|------|
| `test_rate_limit_triggered_after_5_failures` | 5회 실패 후 6번째 요청에서 429 반환 | PASS |

### 3-3. 이미지 업로드 보안 테스트 (`users/tests.py` - `ImageUploadSecurityTest`)

| 테스트 | 검증 내용 | 결과 |
|--------|-----------|------|
| `test_valid_image_accepted` | 정상 JPEG 이미지 업로드 허용 | PASS |
| `test_invalid_extension_rejected` | `.php` 확장자 파일 업로드 거부 및 400 반환 | PASS |
| `test_oversized_image_rejected` | 5MB 초과 파일 업로드 거부 및 400 반환 | PASS |

### 3-4. 결제 정보 노출 방지 테스트 (`payments/tests.py`)

| 테스트 | 검증 내용 | 결과 |
|--------|-----------|------|
| `test_amount_mismatch` | 금액 불일치 응답에 실제 금액 미포함 확인 | PASS |
| `test_portone_api_error` | PortOne 오류 메시지 응답 미노출 확인 | PASS |
| `test_portone_cancel_error` | 취소 API 오류 메시지 응답 미노출 확인 | PASS |

---

## 4. 최종 테스트 결과

```
Ran 67 tests in 39.6s

OK
```

기존 61개 테스트 전부 유지 + 신규 보안 테스트 6개 추가, **67/67 PASS**.

---

## 5. 보안 취약점 보완 요약

| 분류 | 취약점 | 보완 방법 | 상태 |
|------|--------|-----------|------|
| 정보 노출 | 결제 오류/금액 응답 포함 | 로깅 분리, 제네릭 메시지 반환 | 완료 |
| 정보 노출 | 500 에러 내부 정보 노출 | 커스텀 예외 핸들러 fallback 추가 | 완료 |
| 인증 | 로그인 브루트포스 | ScopedRateThrottle (5/min) | 완료 |
| 인증 | 약한 비밀번호 허용 | Django AUTH_PASSWORD_VALIDATORS 연동 | 완료 |
| 파일 업로드 | 확장자·크기 미검증 | 공통 validate_image_file() 유틸리티 | 완료 |
| 설정 | 기본 SECRET_KEY 운영 사용 | 기동 시 sys.exit() 가드 | 완료 |
| 설정 | HTTPS/보안 헤더 미설정 | 운영 환경 조건부 헤더 설정 | 완료 |
