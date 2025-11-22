from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.models import TeacherProfile
from apps.core.permissions import IsAdminOrStaff
from apps.users.serializers.teachers_verification_serializer import (
    TeacherProfileSerializer
)

class TeacherProfileViewSet(viewsets.ModelViewSet):
    queryset = TeacherProfile.objects.select_related("user").all()
    serializer_class = TeacherProfileSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return TeacherProfile.objects.filter(is_verified=False)
        return TeacherProfile.objects.filter(user=user)

    def get_permissions(self):
        if self.action in ["verify_teacher", "unverify_teacher", "destroy"]:
            return [IsAdminOrStaff()]
        elif self.action in ["list"]:
            return [permissions.IsAuthenticated()]
        else:
            return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrStaff])
    def verify_teacher(self, request, pk=None):
        """Verify a teacher only if all required details exist."""
        try:
            teacher = TeacherProfile.objects.select_related("user").get(pk=pk)
        except TeacherProfile.DoesNotExist:
            return Response({"detail": "Teacher not found."}, status=404)
        
        required_fields = [
            teacher.teacher_license_number,
            teacher.teacher_license_certificate,
            teacher.academic_certificate,
            teacher.experience,
            teacher.national_identity_card,
            teacher.national_identity_number,
            teacher.hourly_rate,
        ]

        has_subjects = teacher.subjects.exists()

        if not all(required_fields) or not has_subjects:
            missing = []
            if not teacher.teacher_license_number:
                missing.append("teacher_license_number")
            if not teacher.teacher_license_certificate:
                missing.append("teacher_license_certificate")
            if not teacher.academic_certificate:
                missing.append("academic_certificate")
            if not teacher.experience:
                missing.append("experience")
            if not teacher.national_identity_card:
                missing.append("national_identity_card")
            if not teacher.national_identity_number:
                missing.append("national_identity_number")
            if not teacher.hourly_rate:
                missing.append("hourly_rate")
            if not has_subjects:
                missing.append("subjects")

            return Response(
                {
                    "detail": "Cannot verify. Missing or incomplete fields.",
                    "missing_fields": missing,
                },
                status=status.HTTP_400_BAD_REQUEST,# TODO: send email
            )
        
        teacher.is_verified = True
        teacher.verification_status= 'approved'
        teacher.user.save()
        teacher.save()

        return Response(
            {
                "detail": f"Teacher {teacher.user.first_name} has been verified successfully.",
                "is_verified": teacher.is_verified,
            },
            status=status.HTTP_200_OK, #TODO: send email
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrStaff])
    def unverify_teacher(self, request, pk=None):
        """Revoke verification."""
        try:
            teacher = TeacherProfile.objects.get(pk=pk)
            teacher.is_verified = False
            teacher.verification_status= 'rejected'
            teacher.user.save()
            teacher.save()
            return Response(
                {"detail": f"Teacher {teacher.user.first_name} unverified."},
                status=status.HTTP_200_OK,# rejected
            )
        except TeacherProfile.DoesNotExist:
            return Response({"detail": "Teacher not found."}, status=404)
