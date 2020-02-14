from datetime import datetime, timezone
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
import google_auth_oauthlib.flow
import json
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
from sentry_sdk import capture_message

from account.models import Account
from activity.models import ActivityChange
from auth.backends import CognitoAuthentication
from caracal.common import agol
from caracal.common import google as google_utils
from caracal.common.google import GoogleException
from caracal.common.aws_utils import cloudwatch
from caracal.common.decorators import check_agol_account_connected, check_source_limit
from caracal.common.models import get_num_sources
from drives import serializers
from drives import connections as drives_connections
from drives.models import DriveFileAccount
from outputs.models import AgolAccount


class AddDriveFileAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.AddDriveFileSerializer

    @check_source_limit
    @check_agol_account_connected
    def post(self, request):
        serializer = serializers.AddDriveFileSerializer(data=request.data)
        serializer.is_valid(True)

        user = request.user
        organization = user.organization

        original_data = serializer.validated_data

        # create the drive account, saving the Google tokens
        drive_account = serializer.save(user=request.user)

        # verify that the provider's token is valid and if so remove temporary tokens
        if original_data["provider"] == "google":
            try:
                google_utils.refresh_drive_account_token(drive_account)
            except GoogleException:
                drive_account.delete()
                return Response(
                    {
                        "error": "google_login_required",
                        "message": "Request a new oauth url and log in to Google.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.temp_google_oauth_access_token = None
            user.temp_google_oauth_access_token_expiry = None
            user.temp_google_oauth_refresh_token = None
            user.save()

        # at this point the drive account will have active tokens

        # schedule the function that pulls data from Google Sheets and adds it to S3
        schedule_res = drives_connections.schedule_drives_get_data(
            drive_account, organization
        )
        if "error" in schedule_res:
            return Response(schedule_res, status=status.HTTP_400_BAD_REQUEST)

        drive_account.cloudwatch_get_data_rule_name = schedule_res["rule_name"]
        drive_account.save()

        # schedule AGOL and KML and adds connections
        agol_account = user.agol_account if hasattr(user, "agol_account") else None
        drives_connections.schedule_drives_outputs(
            original_data, drive_account, user, agol_account=agol_account
        )

        # add event
        message = f"{drive_account.provider.capitalize()} account added by {user.name}"
        ActivityChange.objects.create(
            organization=user.organization, account=user, message=message
        )

        return Response(
            {"account_uid": drive_account.uid}, status=status.HTTP_201_CREATED
        )


class DeleteDriveFileAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.DeleteDriveFileSerializer

    def post(self, request):
        serializer = serializers.DeleteDriveFileSerializer(data=request.data)
        serializer.is_valid(True)

        user = request.user

        account_uid = serializer.data["account_uid"]

        try:
            drive_account = DriveFileAccount.objects.get(uid=account_uid)
        except DriveFileAccount.DoesNotExist:
            return Response(
                {
                    "error": "account_does_not_exist",
                    "message": "account does not exist",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if drive_account.organization != request.user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        cloudwatch.delete_cloudwatch_rule(drive_account.cloudwatch_get_data_rule_name)

        drives_connections.delete_drives_kml(drive_account)

        # TODO: delete KML files

        try:
            drives_connections.delete_drives_agol(
                agol_account=user.agol_account, drive_account=drive_account
            )
        except AgolAccount.DoesNotExist:
            pass

        drive_account.is_active = False
        drive_account.save()

        return Response(status=status.HTTP_200_OK)


class GetDriveFileAccountsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetDriveFileAccountsSerializer

    def get_queryset(self):
        organization = self.request.user.organization
        drives = DriveFileAccount.objects.filter(
            organization=organization, is_active=True
        )
        return drives


class GetGoogleDriveFilesView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = serializers.GetGoogleDriveFilesSerializer(
            data=request.query_params
        )
        serializer.is_valid(True)

        file_type = serializer.data["file_type"]

        user = request.user

        # user needs to authenticate again...
        if user.temp_google_oauth_refresh_token is None:
            return Response(
                {
                    "error": "google_login_required",
                    "message": "Request a new oauth url and log in to Google.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        access_token_expiry = user.temp_google_oauth_access_token_expiry

        # test this expiry stuff
        if access_token_expiry and access_token_expiry <= datetime.utcnow().replace(
            tzinfo=timezone.utc
        ):
            # TODO update expiry
            user.temp_google_oauth_access_token = google_utils.refresh_google_token(
                user.temp_google_oauth_refresh_token
            )
            user.save()

        # fixme: documents is None sometimes - possibly to do with the temp tokens?
        documents = google_utils.get_google_drive_files(
            file_type, user.temp_google_oauth_access_token
        )

        if documents is None:
            return Response(
                {
                    "error": "oauth_error",
                    "message": "We experienced an error trying to retrieve your documents.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = {
            "count": len(documents),
            "next": None,
            "previous": None,
            "results": documents,
        }

        return Response(data=data, status=status.HTTP_200_OK)


class GetGoogleSpreadsheetSheetsView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = serializers.GetGoogleDocumentSheetsQueryParamsSerializer(
            data=request.query_params
        )
        serializer.is_valid(True)

        user = request.user

        file_id = serializer.data["file_id"]

        if user.temp_google_oauth_access_token_expiry <= datetime.utcnow().replace(
            tzinfo=timezone.utc
        ):
            user.temp_google_oauth_access_token = google_utils.refresh_google_token(
                user.temp_google_oauth_refresh_token
            )
            user.save()

        spreadsheet = google_utils.get_google_drive_spreadsheet(
            file_id, access_token=user.temp_google_oauth_access_token
        )
        if spreadsheet is not None:
            sheets = spreadsheet["sheets"]

            data = {
                "count": len(sheets),
                "next": None,
                "previous": None,
                "results": [
                    {  # list comprehension!
                        "id": sheet["properties"]["sheetId"],
                        "title": sheet["properties"]["title"],
                    }
                    for sheet in sheets
                ],
            }

            return Response(data=data, status=status.HTTP_200_OK)

        else:
            return Response(
                {
                    "error": "invalid_file",
                    "message": "the file you have request may not be the correct type",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class GetGoogleOauthRequestUrlView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = serializers.GetGoogleOauthRequestUrlQueryParamsSerializer(
            data=request.query_params
        )
        serializer.is_valid(True)

        user = request.user

        action = serializer.data["action"]
        callback = serializer.data.get("callback", "https://caracal.cloud")
        failure_callback = serializer.data.get(
            "failure_callback", "https://caracal.cloud"
        )

        state = {
            "account_uid": str(user.uid_cognito),
            "action": action,
            "callback": callback,
            "failure_callback": failure_callback,
        }

        if action == "login":
            scopes = [
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
            ]
        else:  # drive
            scopes = [
                "openid",
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
            ]

        client_config = google_utils.get_google_client_config()
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config=client_config, scopes=scopes
        )

        flow.redirect_uri = settings.HOSTNAME + reverse("google-oauth-response")

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            login_hint=user.email,
            prompt="consent",
            state=json.dumps(state),
        )

        return Response(
            {"authorization_url": authorization_url, "state": state},
            status=status.HTTP_200_OK,
        )


class GoogleOauthResponseView(views.APIView):

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        serializer = serializers.ReceiveGoogleOauthResponseUrlQueryParamsSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.data

        code, error, state = (
            data.get("code"),
            data.get("error"),
            json.loads(data["state"]),
        )

        account_uid, action, callback, failure_callback = (
            state["account_uid"],
            state["action"],
            state["callback"],
            state["failure_callback"],
        )

        if error is not None:
            capture_message(f"ERROR: {error}")
            return redirect(failure_callback)

        if code is None:
            capture_message(f"ERROR: code is None and error is not None")
            return redirect(state["failure_callback"])

        if action == "login":  # social not currently being used
            scopes = [
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
            ]
        else:  # access to Drive
            scopes = [
                "openid",
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
            ]

        client_config = google_utils.get_google_client_config()
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config=client_config, scopes=scopes
        )

        flow.redirect_uri = settings.HOSTNAME + reverse("google-oauth-response")

        flow.fetch_token(code=code)
        credentials = flow.credentials

        try:
            user = Account.objects.get(uid_cognito=state["account_uid"])
        except Account.DoesNotExist:
            capture_message(f"ERROR: user not found - {account_uid}")
            return redirect(state["failure_callback"])

        else:
            # save temporary tokens which will be copied to the drive account when added
            # possibly fixed with prompt=consent, but if authenticating a second time it only returns access_token
            user.temp_google_oauth_access_token = credentials.token
            user.temp_google_oauth_access_token_expiry = credentials.expiry.replace(
                tzinfo=timezone.utc
            )
            if credentials.refresh_token:
                user.temp_google_oauth_refresh_token = credentials.refresh_token
            else:
                capture_message(
                    f"ERROR: credentials.refresh_token is None - {user.email}"
                )
                return redirect(state["failure_callback"])

            user.save()

        return redirect(state["callback"])


class UpdateDriveFileAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UpdateDriveFileAccountSerializer

    @check_agol_account_connected
    def post(self, request):
        serializer = serializers.UpdateDriveFileAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        organization = user.organization

        update_data = serializer.data
        account_uid = update_data.pop("account_uid")

        try:
            drive_account = DriveFileAccount.objects.get(uid=account_uid)
        except DriveFileAccount.DoesNotExist:
            return Response(
                {
                    "error": "account_does_not_exist",
                    "message": "Drive account does not exist",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # different organization
        if drive_account.organization != user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        update_data.pop("output_agol", None)
        update_data.pop("output_database", None)
        update_data.pop("output_kml", None)

        DriveFileAccount.objects.filter(uid=account_uid).update(**update_data)

        # refresh the provider's token
        if drive_account.provider == "google":
            try:
                google_utils.refresh_drive_account_token(drive_account)
            except GoogleException:
                return Response(
                    {
                        "error": "google_login_required",
                        "message": "Access has been revoked. Remove the drive account and try again.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        drives_connections.update_drives_outputs(serializer.data, drive_account, user)

        message = (
            f"{drive_account.provider.capitalize()} account updated by {user.name}"
        )
        ActivityChange.objects.create(
            organization=user.organization, account=user, message=message
        )

        return Response(status=status.HTTP_200_OK)
