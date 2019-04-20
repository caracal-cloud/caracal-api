from django.conf import settings

from rest_framework import permissions, status, generics
from rest_framework.response import Response

from caracal.common import aws

from public import serializers, tasks


class ContactView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = serializers.ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.data['name']
        email = serializer.data['email']
        area = serializer.data['area']
        message = serializer.data['message']

        email_subject = "Contact - %s" % (area)
        email_message = "Name: %s\nEmail: %s\nArea of Interest: %s\nMessage: %s" % (name, email, area, message)

        tasks.send_email(email_subject, email_message,
                         settings.DEFAULT_EMAIL_SENDER,
                         [settings.DEFAULT_EMAIL_RECIPIENT])

        return Response(status=status.HTTP_200_OK)



class SpeciesSubtypesView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        global_config = aws.get_global_config()
        species_subtypes = global_config['SPECIES_SUBTYPES']
        return Response(status=status.HTTP_200_OK, data=species_subtypes)


