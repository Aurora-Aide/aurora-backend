from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Wrap DRF's default exception handler to normalize unexpected errors to a safe response.
    Keeps the default formatting for known DRF exceptions.
    """
    response = exception_handler(exc, context)

    if response is not None:
        return response

    # Fallback for unhandled exceptions
    view_name = None
    if context and context.get("view") is not None:
        view_name = context["view"].__class__.__name__
    logger.exception("Unhandled exception in DRF view %s", view_name, exc_info=exc)

    return Response(
        {"detail": "Internal server error"},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

