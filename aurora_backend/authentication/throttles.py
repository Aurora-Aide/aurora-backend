from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class LoginThrottle(UserRateThrottle):
    scope = "login"


class RegisterThrottle(AnonRateThrottle):
    scope = "register"


class LogoutThrottle(UserRateThrottle):
    scope = "logout"


class DeleteUserThrottle(UserRateThrottle):
    scope = "delete_user"

