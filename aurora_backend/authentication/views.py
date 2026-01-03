from datetime import datetime

from rest_framework import status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenRefreshView

from .models import User
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, UpdateNamesSerializer
from .services import (
    blacklist_refresh_token,
    delete_user_and_blacklist,
    issue_tokens_for_user,
)
from .throttles import (
    DeleteUserThrottle,
    LoginThrottle,
    LogoutThrottle,
    RegisterThrottle,
)

class RegisterView(APIView):
    throttle_classes = [RegisterThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = issue_tokens_for_user(user)
            userData = UserSerializer(user).data
            return Response(
                {
                    "access": tokens["access"],
                    "refresh": tokens["refresh"],
                    "user": userData,
                },
                status=status.HTTP_200_OK,
            )
        
        errorMessages = " ".join([" ".join(messages) for messages in serializer.errors.values()])
        return Response({"detail": errorMessages}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(views.APIView):
    permission_classes = []
    throttle_classes = [LoginThrottle]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            tokens = issue_tokens_for_user(user)
            userData = UserSerializer(user).data
            return Response(
                {
                    "access": tokens["access"],
                    "refresh": tokens["refresh"],
                    "user": userData,
                },
                status=status.HTTP_200_OK,
            )
        
        errorMessages = " ".join([" ".join(messages) for messages in serializer.errors.values()])
        return Response({"detail": errorMessages}, status=status.HTTP_400_BAD_REQUEST)
    

class LogoutView(APIView):
    throttle_classes = [LogoutThrottle]

    def post(self, request):
        try:
            refreshToken = request.data.get("refresh")
            if refreshToken is None:
                return Response({"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                blacklist_refresh_token(refreshToken)
            except TokenError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"detail": "Logout successful."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class GetAllUsersView(APIView):
    def get(self, request):
        users = User.objects.all()        
        serializer = UserSerializer(users, many=True)        
        return Response(serializer.data, status=status.HTTP_200_OK)
 
class GetUserView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        userData = UserSerializer(user).data
        return Response(userData, status=status.HTTP_200_OK)
    
class UpdateNamesView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = UpdateNamesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        first_name = serializer.validated_data.get("first_name")
        last_name = serializer.validated_data.get("last_name")

        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name

        user.save()

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    def put(self, request):
        return self.patch(request)
    
class RefreshAccessTokenView(TokenRefreshView):
    serializer_class = TokenRefreshSerializer

class DeleteUserView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [DeleteUserThrottle]
    
    def delete(self, request):
        try:
            user_email = request.data.get("user_email")
            if user_email is None:
                return Response(
                    {"detail": "User Email is required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if request.user.email != user_email:
                return Response(
                    {"detail": "You can only delete your own account."}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            user = request.user
            delete_user_and_blacklist(user)
            
            return Response(
                {"detail": "User account and all associated data deleted successfully."}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

