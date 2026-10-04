from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken
from djmoney.money import Money

from apps.core.models import User, OnboardingStep
from apps.core.auth.serializers.auth_serializer import CustomTokenObtainPairSerializer
from apps.users.serializers.onboarding_serializers import (
    OnboardingStep2Serializer,
    OnboardingStep3Serializer,
)
from apps.users.services.onboarding_service import (
    assert_can_access_step,
    get_step_number,
    get_resume_route,
    get_user_draft_data,
)
from apps.transactions.models import Wallet


class OnboardingStep2View(generics.GenericAPIView):
    """
    PATCH /api/v1/onboarding/step-2/
    Handles Student curriculum/grade, Teacher personal KYC identity,
    and Parent learner linking per SAD §7.3.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    serializer_class = OnboardingStep2Serializer

    def patch(self, request, *args, **kwargs):
        assert_can_access_step(request.user, OnboardingStep.STEP_2_PROFILE)

        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response(
            {
                "status": "success",
                "message": "Step 2 profile data saved successfully.",
                "data": result,
            },
            status=status.HTTP_200_OK,
        )


class OnboardingStep3View(generics.GenericAPIView):
    """
    PATCH /api/v1/onboarding/step-3/
    Handles Student goals, Teacher qualifications/KYC certificates/rates,
    and Parent billing phone/rules per SAD §7.4.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    serializer_class = OnboardingStep3Serializer

    def patch(self, request, *args, **kwargs):
        assert_can_access_step(request.user, OnboardingStep.STEP_3_ACADEMIC_KYC)

        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response(
            {
                "status": "success",
                "message": "Step 3 academic details saved successfully.",
                "data": result,
            },
            status=status.HTTP_200_OK,
        )


class OnboardingCompleteView(generics.GenericAPIView):
    """
    POST /api/v1/onboarding/complete/
    Sets onboarding_step = 'completed', activates account, auto-provisions KES wallet,
    and returns refreshed JWT pair and target dashboard URL per SAD §7.5.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user: User = request.user
        assert_can_access_step(user, OnboardingStep.STEP_4_LAUNCH)

        # 1. Finalize User state
        user.onboarding_step = OnboardingStep.COMPLETED
        user.account_confirmed = True
        user.save(update_fields=["onboarding_step", "account_confirmed"])

        # 2. Ensure initial KES wallet is provisioned
        account_type = user.role if user.role in ["student", "teacher", "parent"] else "student"
        Wallet.objects.get_or_create(
            user=user,
            defaults={
                "account_type": account_type,
                "balance": Money(0.00, "KES"),
                "is_active": True,
            },
        )

        # 3. Generate fresh JWT tokens with updated claims
        refresh = RefreshToken.for_user(user)
        refresh["is_superuser"] = user.is_superuser
        refresh["email"] = user.email
        refresh["first_name"] = user.first_name
        refresh["role"] = getattr(user, "role", None)
        profile_id = CustomTokenObtainPairSerializer.get_profile_id(user)
        if profile_id:
            refresh["profile_id"] = profile_id
        refresh["onboarding_step"] = OnboardingStep.COMPLETED
        refresh["is_onboarded"] = True

        role = user.role or "student"
        dashboard_url = f"/{role}-dashboard/home"

        return Response(
            {
                "status": "success",
                "message": "Onboarding completed successfully. Welcome to StudyBuddy Africa!",
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
                "data": {
                    "onboarding_step": OnboardingStep.COMPLETED,
                    "dashboard_url": dashboard_url,
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "role": user.role,
                        "onboarding_step": OnboardingStep.COMPLETED,
                        "is_onboarded": True,
                        "account_confirmed": True,
                    },
                },
            },
            status=status.HTTP_200_OK,
        )


class OnboardingStatusView(generics.GenericAPIView):
    """
    GET /api/v1/onboarding/status/
    Returns current onboarding_step, numeric step index, completed status,
    canonical resume URL, and draft state for frontend hydration per SAD §7.6.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user: User = request.user
        step = getattr(user, "onboarding_step", OnboardingStep.PENDING_OTP)
        is_completed = (step == OnboardingStep.COMPLETED)

        return Response(
            {
                "status": "success",
                "data": {
                    "user_id": str(user.id),
                    "email": user.email,
                    "role": getattr(user, "role", "student"),
                    "onboarding_step": step,
                    "step_number": get_step_number(step),
                    "is_completed": is_completed,
                    "resume_route": get_resume_route(user),
                    "draft_data": get_user_draft_data(user),
                },
            },
            status=status.HTTP_200_OK,
        )
