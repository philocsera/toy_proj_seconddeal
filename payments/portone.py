import requests
from django.conf import settings

PORTONE_AUTH_URL = 'https://api.iamport.kr/users/getToken'
PORTONE_PAYMENT_URL = 'https://api.iamport.kr/payments/{imp_uid}'
PORTONE_CANCEL_URL = 'https://api.iamport.kr/payments/cancel'


def _get_portone_token() -> str:
    resp = requests.post(PORTONE_AUTH_URL, json={
        'imp_key': settings.PORTONE_IMP_KEY,
        'imp_secret': settings.PORTONE_IMP_SECRET,
    }, timeout=10)
    resp.raise_for_status()
    return resp.json()['response']['access_token']


def fetch_payment(imp_uid: str) -> dict:
    """PortOne 서버에서 결제 정보를 직접 조회 (위변조 방지)"""
    token = _get_portone_token()
    resp = requests.get(
        PORTONE_PAYMENT_URL.format(imp_uid=imp_uid),
        headers={'Authorization': token},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()['response']


def cancel_payment(imp_uid: str, reason: str = '구매자 요청') -> dict:
    """PortOne 결제 취소"""
    token = _get_portone_token()
    resp = requests.post(
        PORTONE_CANCEL_URL,
        headers={'Authorization': token},
        json={'imp_uid': imp_uid, 'reason': reason},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()['response']
