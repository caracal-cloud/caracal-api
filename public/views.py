from django.conf import settings

from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from caracal.common.aws_utils import dynamodb

from public import serializers, tasks


class ContactView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.ContactMessageSerializer
    throttle_classes = [AnonRateThrottle]

    # rate limit this thing...
    def post(self, request):
        serializer = serializers.ContactMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.data['name']
        email = serializer.data['email']
        message = serializer.data['message']

        email_subject = "Contact from submission"
        email_message = f'Name: {name}\nEmail: {email}\nMessage: {message}'

        tasks.send_email(email_subject, email_message,
                         settings.DEFAULT_EMAIL_SENDER,
                         [settings.DEFAULT_EMAIL_RECIPIENT])

        return Response(status=status.HTTP_200_OK)


class SpeciesSubtypesView(views.APIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        global_config = dynamodb.get_global_config()
        species_subtypes = global_config['SPECIES_SUBTYPES']
        return Response(status=status.HTTP_200_OK, data=species_subtypes)


