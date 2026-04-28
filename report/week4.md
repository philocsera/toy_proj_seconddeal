# Week 4 Report — 마무리·정리·회고

**기간:** 2026-04-28  
**목표:** 에러 핸들링 통일, 입력값 검증 보강, Postman 컬렉션 작성, README 최종화, 전체 회고

---

## 완료 항목

| 항목 | 상태 |
|---|---|
| 커스텀 exception handler (에러 응답 형태 통일) | 완료 |
| 상품 가격 범위 검증 (100원 ~ 1억원) | 완료 |
| 상품 제목 최소 길이 검증 (2자 이상) | 완료 |
| 회원가입 닉네임 검증 (2~20자) | 완료 |
| 중복 이메일 커스텀 에러 메시지 | 완료 |
| Postman 컬렉션 작성 (`postman_collection.json`) | 완료 |
| README 아키텍처 다이어그램 추가 | 완료 |
| README 카카오 OAuth2 플로우, 결제 위변조 방지 플로우 시각화 | 완료 |

---

## 에러 핸들링 설계

### 문제
DRF 기본 에러 응답은 형태가 제각각이다.

```json
// 필드 에러
{ "price": ["가격은 100원 이상이어야 합니다."] }

// detail 에러
{ "detail": "인증 자격 증명이 제공되지 않았습니다." }
```

### 해결: 커스텀 exception handler

```python
# config/exceptions.py
def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        if isinstance(error_detail, dict) and 'detail' not in error_detail:
            # 필드 에러를 단일 detail 문자열로 변환
            messages = [f'{field}: {errors[0]}' for field, errors in error_detail.items()]
            response.data = {'detail': ' / '.join(messages)}
        response.data['status_code'] = response.status_code
    return response
```

### 결과: 모든 에러가 동일한 형태로 통일

```json
{ "detail": "price: 가격은 100원 이상이어야 합니다.", "status_code": 400 }
{ "detail": "nickname: 닉네임은 2자 이상이어야 합니다.", "status_code": 400 }
{ "detail": "email: 이미 사용 중인 이메일입니다.", "status_code": 400 }
```

---

## 실제 검증 테스트 결과

| 케이스 | 입력 | 응답 |
|---|---|---|
| 가격 50원 | `price: 50` | 400, "가격은 100원 이상이어야 합니다." |
| 닉네임 1자 | `nickname: "A"` | 400, "닉네임은 2자 이상이어야 합니다." |
| 중복 이메일 | 기존 이메일로 재가입 | 400, "이미 사용 중인 이메일입니다." |
| 판매완료 상품 주문 | `product_id: 판매완료상품` | 400, "판매중인 상품이 아닙니다." |
| 타인 상품 수정 | PUT /products/<타인상품>/ | 403, PermissionDenied |

---

## Postman 컬렉션

`postman_collection.json` 파일에 전체 API 15개 엔드포인트를 수록했다.

**특징:**
- 로그인 요청 성공 시 `Test` 스크립트로 `access_token`을 컬렉션 변수에 자동 저장
- 이후 모든 인증 필요 요청에서 `Bearer {{access_token}}` 자동 적용
- `base_url` 변수로 로컬/운영 환경 전환 가능

---

## 4주간 전체 회고

### 1주차 — Django 세팅 + DB 설계

**배운 것:**
- `AbstractBaseUser`로 커스텀 User 모델 작성 시 `create_superuser`도 반드시 구현해야 한다
- `AUTH_USER_MODEL`은 앱 등록보다 먼저 설정해야 FK 마이그레이션 의존성이 깨지지 않는다
- MySQL `ENUM`은 값 추가 시 테이블 잠금이 걸려 운영 중 변경이 위험하다 → `VARCHAR + TextChoices` 패턴이 안전하다

**면접 답변 포인트:**
"MySQL ENUM 대신 VARCHAR + Django TextChoices를 선택한 이유가 무엇인가요?"
→ ENUM은 값 추가 시 ALTER TABLE이 발생하고 InnoDB에서 Full Table Lock이 걸린다. 트래픽이 있는 상황에서 필드 값 하나를 추가하는 것이 배포 리스크가 된다. TextChoices로 관리하면 DB 스키마 변경 없이 Python 코드만 수정해도 된다.

---

### 2주차 — 소셜 로그인 + 결제 연동

**배운 것:**
- `django-allauth`의 소셜 로그인은 세션 기반 리다이렉트 방식이라 JWT API 서버에 그대로 쓰기 어렵다. 라이브러리를 `SocialAccount` 모델 관리 용도로만 쓰고, OAuth2 플로우는 `requests`로 직접 구현했다
- 카카오 계정에 이메일이 없는 경우를 처리하지 않으면 `IntegrityError`가 발생한다
- 결제 위변조 방지: 클라이언트가 보낸 금액을 믿으면 안 된다. `imp_uid`로 PortOne에 직접 조회해 서버에서 금액을 재검증해야 한다
- `merchant_uid`는 DB `unique=True`와 `uuid4`로 이중 보호한다

**면접 답변 포인트:**
"결제 위변조를 어떻게 방지했나요?"
→ 클라이언트가 결제 완료 후 `imp_uid`와 `merchant_uid`를 보내면, 서버는 PortOne REST API에 `imp_uid`로 직접 결제 정보를 조회합니다. DB에 저장된 주문 금액과 PortOne에서 실제 승인된 금액을 비교해 불일치 시 400을 반환하고 주문을 처리하지 않습니다.

---

### 3주차 — 서버 배포 + 서버 이전

**배운 것:**
- Nginx가 앞단에 필요한 이유: 정적 파일 서빙, SSL 종단, Slowloris 공격 방어, 요청 버퍼링
- `systemctl reload nginx`는 기존 커넥션을 끊지 않고 설정만 리로드한다 → 무중단 트래픽 전환 가능
- `mysqldump --single-transaction`은 InnoDB에서 테이블 잠금 없이 일관된 스냅샷을 뜬다
- DB 이전 순서: DB 덤프 → B에 복원 → 코드 배포 → migrate (순서가 바뀌면 스키마 불일치 발생)
- `.env` 파일 관리가 배포의 핵심: 코드는 git으로 배포하지만 `.env`는 `scp`로 직접 전달

**면접 답변 포인트:**
"서버 이전 경험을 설명해주세요."
→ EC2 인스턴스 A에서 `mysqldump --single-transaction`으로 DB를 백업하고 `scp`로 인스턴스 B에 전송한 뒤 복원했습니다. 코드를 재배포하고 `migrate`를 실행한 다음, Nginx의 `proxy_pass`를 B로 변경하고 `systemctl reload`로 트래픽을 전환했습니다. `reload`는 기존 커넥션을 유지하므로 다운타임이 없었습니다.

---

### 4주차 — 마무리

**배운 것:**
- DRF의 `UniqueValidator`는 필드 레벨 `validate_` 메서드보다 먼저 실행된다. 커스텀 에러 메시지를 넣으려면 필드 선언 시 `validators=[UniqueValidator(..., message='...')]`로 지정해야 한다
- 에러 응답 형태를 통일하면 프론트엔드가 에러를 처리하는 코드를 하나로 줄일 수 있다

---

## 프로젝트 최종 파일 구조

```
0428/
├── config/
│   ├── settings.py       # DB분기, JWT, allauth, 커스텀 예외 핸들러
│   ├── urls.py           # 전체 라우팅
│   └── exceptions.py     # 커스텀 exception handler
├── users/
│   ├── models.py         # AbstractBaseUser, provider 필드
│   ├── serializers.py    # 회원가입·로그인·JWT 응답
│   ├── views.py          # 회원가입, 로그인, 내정보
│   ├── kakao.py          # 카카오 OAuth2 커스텀 뷰
│   └── urls.py
├── products/
│   ├── models.py         # Product (TextChoices ENUM)
│   ├── serializers.py    # 가격·제목 검증 포함
│   ├── views.py          # CRUD, 상태변경, 내상품
│   └── urls.py
├── orders/
│   ├── models.py         # Order (merchant_uid unique)
│   ├── serializers.py    # 주문생성, 상품상태 자동변경
│   ├── views.py
│   └── urls.py
├── payments/
│   ├── models.py         # Payment (OneToOne→Order)
│   ├── portone.py        # PortOne REST API 연동
│   ├── views.py          # 검증, 취소, 체크아웃 페이지
│   ├── urls.py
│   └── templates/payments/checkout.html
├── deploy/
│   ├── nginx.conf        # Nginx 프록시 설정
│   ├── gunicorn.service  # systemd 서비스
│   ├── deploy.sh         # EC2 초기 배포 스크립트
│   ├── migrate_db.sh     # 서버 이전 스크립트
│   └── mysql_setup.sql   # MySQL DB 초기 세팅
├── report/
│   ├── week1.md
│   ├── week2.md
│   ├── week3.md
│   └── week4.md
├── postman_collection.json
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

---

## 면접 준비 체크리스트

- [ ] AbstractBaseUser vs AbstractUser 차이 설명
- [ ] MySQL ENUM vs VARCHAR+TextChoices 선택 이유
- [ ] JWT Access/Refresh 토큰 분리 이유와 갱신 플로우
- [ ] 카카오 OAuth2 인가코드 플로우 화이트보드 설명
- [ ] 결제 위변조 방지 메커니즘
- [ ] Nginx + Gunicorn 역할 분리
- [ ] mysqldump --single-transaction 옵션 이유
- [ ] 서버 이전 시 다운타임 최소화 방법
- [ ] DRF `IsAuthenticatedOrReadOnly` vs `IsAuthenticated` 차이
- [ ] OneToOneField vs ForeignKey 선택 기준 (Payment ↔ Order)
