
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response


class AgolOauthView(views.APIView):

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(status=status.HTTP_200_OK)


class GoogleOauthView(views.APIView):

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(status=status.HTTP_200_OK)