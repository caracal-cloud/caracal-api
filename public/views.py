from django.conf import settings

from rest_framework import permissions, status, generics
from rest_framework.response import Response
import traceback

from public import serializers, tasks


class ContactView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.ContactSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.data['name']
        email = serializer.data['email']
        area = serializer.data['area']
        message = serializer.data['message']

        email_subject = "Contact - %s" % (area)
        email_message = "Name: %s\nEmail: %s\nArea of Interest: %s\nMessage: %s" % (name, email, area, message)

        tasks.send_email.delay(email_subject, email_message,
                               settings.DEFAULT_EMAIL_RECIPIENT, [settings.DEFAULT_EMAIL_RECIPIENT])

        return Response(status=status.HTTP_200_OK)




