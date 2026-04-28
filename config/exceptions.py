import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_detail = response.data
        if isinstance(error_detail, dict) and 'detail' not in error_detail:
            messages = []
            for field, errors in error_detail.items():
                if isinstance(errors, list):
                    messages.append(f'{field}: {errors[0]}')
                else:
                    messages.append(f'{field}: {errors}')
            response.data = {'detail': ' / '.join(messages)}

        response.data['status_code'] = response.status_code

    else:
        # DRF가 처리하지 못한 예외(500) — 내부 정보를 클라이언트에 노출하지 않음
        logger.exception('Unhandled exception in view: %s', exc)
        response = Response(
            {'detail': '서버 오류가 발생했습니다.', 'status_code': 500},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
