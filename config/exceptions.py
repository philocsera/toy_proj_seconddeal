from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        # DRF 에러를 { "detail": "...", "code": "..." } 형태로 통일
        error_detail = response.data
        if isinstance(error_detail, dict) and 'detail' not in error_detail:
            # 필드 검증 에러: { "field": ["msg"] } → { "detail": "field: msg" }
            messages = []
            for field, errors in error_detail.items():
                if isinstance(errors, list):
                    messages.append(f'{field}: {errors[0]}')
                else:
                    messages.append(f'{field}: {errors}')
            response.data = {'detail': ' / '.join(messages)}

        response.data['status_code'] = response.status_code

    return response
