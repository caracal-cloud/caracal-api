from datetime import datetime, timezone
import json
import requests
from rest_framework import permissions, status, generics
from rest_framework.response import Response

from activity.models import ActivityChange
from auth.backends import CognitoAuthentication
from caracal.common import agol, connections
from caracal.common.aws_utils import cloudwatch, dynamodb
from caracal.common.decorators import check_agol_account_connected, check_source_limit
from caracal.common.models import get_num_sources, RealTimeAccount, RealTimeIndividual
import caracal.common.serializers as common_serializers
from collars import connections as collar_connections
from collars import serializers as collar_serializers
from outputs.models import AgolAccount


class AddCollarAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = collar_serializers.AddCollarAccountSerializer

    @check_source_limit
    @check_agol_account_connected
    def post(self, request):
        serializer = collar_serializers.AddCollarAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        organization = user.organization

        data = serializer.validated_data
        species = data["type"]
        provider = data["provider"]

        if provider == "orbcomm":
            title = f"{species.capitalize()} - Orbcomm"
        elif provider == "savannah_tracking":
            title = f"{species.capitalize()} - Savannah Tracking"
        else:
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )  # validated in serializer

        collar_account = RealTimeAccount.objects.create(
            organization=organization,
            is_active=True,
            source="collar",
            provider=provider,
            type=species,
            title=title,
        )

        # input - setup CloudWatch rule to fetch positions
        schedule_res = collar_connections.schedule_collars_get_data(
            data, collar_account, organization
        )
        if "error" in schedule_res:
            return Response(schedule_res, status=status.HTTP_400_BAD_REQUEST)

        collar_account.cloudwatch_get_data_rule_name = schedule_res["rule_name"]
        collar_account.save()

        agol_account = user.agol_account if hasattr(user, "agol_account") else None
        connections.schedule_realtime_outputs(
            data, species, "collar", collar_account, user, agol_account=agol_account
        )

        message = f"{species} collar account added by {user.name}"
        ActivityChange.objects.create(
            organization=user.organization, account=user, message=message
        )

        return Response(
            {"account_uid": collar_account.uid}, status=status.HTTP_201_CREATED
        )


class DeleteCollarAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = common_serializers.DeleteAccountSerializer

    def post(self, request):
        serializer = common_serializers.DeleteAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # TODO: verify that all CF rules being removed

        user, data = request.user, serializer.data

        try:
            realtime_account = RealTimeAccount.objects.get(
                uid=data["account_uid"], is_active=True
            )
        except RealTimeAccount.DoesNotExist:
            return Response(
                {
                    "error": "account_does_not_exist",
                    "message": "account does not exist",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if realtime_account.organization != request.user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        cloudwatch.delete_cloudwatch_rule(
            realtime_account.cloudwatch_get_data_rule_name
        )

        connections.delete_realtime_kml(realtime_account)

        try:  # if agol account exists, try to delete connection...
            connections.delete_realtime_agol(
                agol_account=user.agol_account, realtime_account=realtime_account
            )
        except AgolAccount.DoesNotExist:
            pass

        realtime_account.is_active = False
        realtime_account.datetime_deleted = datetime.utcnow().replace(
            tzinfo=timezone.utc
        )  # TODO: use shared function
        realtime_account.save()

        return Response(status=status.HTTP_200_OK)


class GetCollarAccountsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = collar_serializers.GetCollarAccountsSerializer

    def get_queryset(self):
        user = self.request.user
        return RealTimeAccount.objects.filter(
            is_active=True, organization=user.organization, source="collar"
        )


class GetCollarAccountDetailView(generics.RetrieveAPIView):

    lookup_field = "uid"
    serializer_class = collar_serializers.GetCollarAccountDetailSerializer
    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return RealTimeAccount.objects.filter(
            is_active=True, organization=user.organization, source="collar"
        )


class GetCollarIndividualsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = collar_serializers.GetCollarIndividualsSerializer

    def get_queryset(self):

        serializer = common_serializers.GetRtIndividualsQueryParamsSerializer(
            data=self.request.query_params
        )
        serializer.is_valid(raise_exception=True)

        account_uid = serializer.data["account_uid"]
        user = self.request.user

        try:
            account = RealTimeAccount.objects.get(
                is_active=True, organization=user.organization, uid=account_uid
            )
            if account.source != "collar":
                return RealTimeIndividual.objects.none()
        except RealTimeAccount.DoesNotExist:
            return RealTimeIndividual.objects.none()

        return RealTimeIndividual.objects.filter(is_active=True, account=account)


class GetCollarIndividualDetailView(generics.RetrieveAPIView):

    lookup_field = "uid"
    serializer_class = collar_serializers.GetCollarIndividualDetailSerializer
    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RealTimeIndividual.objects.filter(
            account__organization=self.request.user.organization
        )


class UpdateCollarAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = common_serializers.UpdateRtAccountSerializer

    def post(self, request):
        serializer = common_serializers.UpdateRtAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        update_data = serializer.data
        account_uid = update_data.pop("account_uid")

        if update_data.get("output_agol", False):
            try:
                agol_account = user.agol_account
            except AgolAccount.DoesNotExist:
                return Response(
                    {
                        "error": "agol_account_required",
                        "message": "ArcGIS Online account required",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            realtime_account = RealTimeAccount.objects.get(
                uid=account_uid, is_active=True
            )
        except RealTimeAccount.DoesNotExist:
            return Response(
                {
                    "error": "account_does_not_exist",
                    "message": "collar account does not exist",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if realtime_account.organization != user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        update_data.pop("output_agol", None)
        update_data.pop("output_database", None)
        update_data.pop("output_kml", None)

        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        RealTimeAccount.objects.filter(uid=account_uid).update(
            datetime_updated=now, **update_data
        )

        # TODO: if updating title and has AGOL connection, then update title in ArcGIS
        connections.update_realtime_outputs(serializer.data, realtime_account, user)

        message = f"{realtime_account.type} collar account updated by {user.name}"
        ActivityChange.objects.create(
            organization=user.organization, account=user, message=message
        )

        return Response(status=status.HTTP_200_OK)


class UpdateCollarIndividualView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = collar_serializers.UpdateCollarIndividualSerializer

    def post(self, request):
        serializer = collar_serializers.UpdateCollarIndividualSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        user = request.user

        update_data = serializer.data
        individual_uid = update_data.pop("individual_uid")

        try:
            individual = RealTimeIndividual.objects.get(
                uid=individual_uid, is_active=True
            )
        except RealTimeIndividual.DoesNotExist:
            return Response(
                {
                    "error": "individual_does_not_exist",
                    "message": "individual does not exist",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            individual.account.organization != user.organization
            and not user.is_superuser
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # do this before updating individual so we know old values
        # if there is a connected AGOL layer, update features in the layer on device_id
        agol_connections = individual.account.connections.filter(
            agol_account__isnull=False
        )
        for agol_connection in agol_connections:

            attributes = dict()
            if "name" in update_data and update_data["name"] != individual.name:
                attributes["Name"] = update_data["name"]

            if (
                "subtype" in update_data
                and update_data["subtype"] != individual.subtype
            ):
                attributes["Type"] = update_data["subtype"]

            if "sex" in update_data and update_data["sex"] != individual.subtype:
                attributes["Sex"] = update_data["sex"]

            if "status" in update_data and update_data["status"] != individual.subtype:
                attributes["Status"] = update_data["status"]

            if len(attributes) > 0:

                agol_account = agol_connection.agol_account

                # TODO: this is grossly inefficient, but AGOL doesn't seem to have an update with where clause

                features = agol.get_collar_features(
                    device_id=individual.device_id,
                    layer_id=agol_connection.agol_layer_id,
                    feature_service_url=agol_account.feature_service_url,
                    agol_account=agol_account
                )

                print(f'Updating {len(features)} features')
                updates = [(f.id, attributes, None) for f in features]  

                agol.update_features(
                    updates=updates,
                    layer_id=agol_connection.agol_layer_id,
                    feature_service_url=agol_account.feature_service_url,
                    agol_account=agol_account
                )

        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        RealTimeIndividual.objects.filter(uid=individual_uid).update(
            datetime_updated=now, **update_data
        )

        message = f"{individual.account.type} collar individual updated by {user.name}"
        ActivityChange.objects.create(
            organization=user.organization, account=user, message=message
        )

        return Response(status=status.HTTP_200_OK)


class ValidateAccountDetailsView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = collar_serializers.ValidateAccountDetailsSerializer

    def post(self, request):
        serializer = collar_serializers.ValidateAccountDetailsSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        global_config = dynamodb.get_global_config()

        provider = serializer.data["provider"]

        if provider == "orbcomm":
            orbcomm_company_id = serializer.data["orbcomm_company_id"]
            orbcomm_timezone = serializer.data["orbcomm_timezone"]
            orbcomm_list_url = global_config["ORBCOMM_BASE_URL"] + "getUnitList"

            payload = {
                "company": orbcomm_company_id,
                "tz": orbcomm_timezone,
                "lmtime": orbcomm_timezone,
            }

            res = requests.get(
                orbcomm_list_url, params=payload
            )  # status_code is always 200
            rows = parse_orbcomm_rows(res)
            is_verified = len(rows) > 0

        elif provider == "savannah_tracking":
            savannah_tracking_username = serializer.data["savannah_tracking_username"]
            savannah_tracking_password = serializer.data["savannah_tracking_password"]

            login_payload = {
                "request": "authenticate",
                "uid": savannah_tracking_username,
                "pwd": savannah_tracking_password,
            }

            savannah_tracking_login_url = (
                global_config["SAVANNAH_TRACKING_BASE_URL"] + "savannah_data/data_auth"
            )
            login_res = requests.post(savannah_tracking_login_url, data=login_payload)
            login_content = login_res.json()
            is_verified = "sucess" in login_content.keys() and login_content["sucess"]

        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if is_verified:
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(
                {
                    "error": "invalid_collar_account_details",
                    "message": "invalid collar account details",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )


def parse_orbcomm_rows(res):

    content = res.content.decode("utf-8")
    content = content.replace('<?xml version="1.0" encoding="utf-8"?>\n', "")
    content = content.replace('<string xmlns="http://tempuri.org/">', "")
    content = content.replace("</string>", "")

    rows = content.split("~")
    rows = [row.split("`") for row in rows]
    rows = rows[1:]

    return rows
