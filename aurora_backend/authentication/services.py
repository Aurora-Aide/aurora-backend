from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.exceptions import TokenError


def issue_tokens_for_user(user):
    """
    Helper to generate refresh + access tokens for a user.
    Returns a dict with stringified tokens.
    """
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def blacklist_refresh_token(refresh_token: str):
    """
    Blacklist a single refresh token string.
    Raises TokenError if the token is invalid/expired.
    """
    token = RefreshToken(refresh_token)
    token.blacklist()


@transaction.atomic
def blacklist_all_user_tokens(user):
    """
    Blacklist every outstanding token for a user.
    Idempotent: safe to call multiple times.
    """
    outstanding_tokens = OutstandingToken.objects.filter(user=user)
    for token in outstanding_tokens:
        BlacklistedToken.objects.get_or_create(token=token)


@transaction.atomic
def delete_user_and_blacklist(user):
    """
    Blacklist all tokens and delete the user in one atomic operation.
    """
    blacklist_all_user_tokens(user)
    user.delete()

