from rest_framework import generics, permissions, filters
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from apps.users.serializers.list_users_serliazer import UserSerializer
from apps.core.models import User
from apps.users.models import TeacherProfile, StudentProfile, ParentProfile
from apps.school.models import CourseEnrollment
from apps.transactions.models import Wallet
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie


class UserListView(generics.ListAPIView):
    """
    Retrieve users with permission control:
      - Superuser → can view all users.
      - Regular user → can only view their own info.
    Supports filtering by role and email.
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["email", "first_name", "last_name"]

    def get_queryset(self):
        user = self.request.user

        queryset = (
            User.objects.select_related(
                "teacher_profile", "parent_profile", "student_profile"
            )
            .only(
                "id",
                "email",
                "first_name",
                "last_name",
                "username",
                "role",
                "is_active",
                "is_staff",
                "account_confirmed",
                # profile PKs
                "teacher_profile__id",
                "parent_profile__id",
                "student_profile__id",
            )
            .order_by("-created_at")
        )

        role = self.request.query_params.get("role")
        email = self.request.query_params.get("email")

        if role:
            queryset = queryset.filter(role__iexact=role.strip())

        if email:
            queryset = queryset.filter(email__icontains=email.strip())

        if user.is_superuser:
            return queryset

        return queryset.filter(id=user.id)

    @method_decorator(cache_page(60 * 60 * 2))
    @method_decorator(vary_on_cookie)
    def list(self, request, *args, **kwargs):
        """Custom response structure."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"count": queryset.count(), "results": serializer.data})


class UserDetailView(generics.RetrieveAPIView):
    """Retrieve single user detail"""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return User.objects.all()
        return User.objects.filter(id=user.id)


class CurrentUserView(generics.RetrieveAPIView):
    """Retrieve current authenticated user details."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class TeacherMeView(generics.GenericAPIView):
    """Detailed current teacher context endpoint."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            teacher = (
                TeacherProfile.objects.select_related("school")
                .prefetch_related(
                    "subjects",
                    "grade",
                    "teacher_courses__subject",
                    "teacher_courses__grade",
                    "teacher_courses__education_level",
                )
                .get(user=user)
            )
        except TeacherProfile.DoesNotExist as exc:
            raise PermissionDenied("No teacher profile found for this user.") from exc

        wallet = Wallet.objects.filter(user=user).first()
        courses = teacher.teacher_courses.all()

        return Response(
            {
                "user": UserSerializer(user).data,
                "profile": {
                    "id": str(teacher.id),
                    "is_verified": teacher.is_verified,
                    "verification_status": teacher.verification_status,
                    "bio": teacher.bio,
                    "phone": teacher.phone,
                    "experience": teacher.experience,
                    "education_level": (
                        {
                            "id": str(teacher.education_level.id),
                            "name": teacher.education_level.name,
                        }
                        if teacher.education_level
                        else None
                    ),
                    "school": (
                        {
                            "id": str(teacher.school.id),
                            "name": teacher.school.name,
                            "city": teacher.school.city,
                            "country": teacher.school.country,
                        }
                        if teacher.school
                        else None
                    ),
                    "subjects": [
                        {"id": str(subject.id), "name": subject.name}
                        for subject in teacher.subjects.all()
                    ],
                    "grades": [
                        {"id": str(grade.id), "level": grade.level}
                        for grade in teacher.grade.all()
                    ],
                },
                "wallet": (
                    {
                        "id": str(wallet.id),
                        "balance": str(wallet.balance.amount),
                        "currency": str(wallet.balance.currency),
                        "account_type": wallet.account_type,
                    }
                    if wallet
                    else None
                ),
                "courses": [
                    {
                        "id": str(course.id),
                        "title": course.title,
                        "subject": course.subject.name if course.subject else None,
                        "grade": course.grade.level if course.grade else None,
                        "education_level": (
                            course.education_level.name
                            if course.education_level
                            else None
                        ),
                        "price": str(course.price.amount),
                        "currency": str(course.price.currency),
                        "is_active": course.is_active,
                        "enrollments_count": course.enrollments.count(),
                    }
                    for course in courses
                ],
            },
            status=status.HTTP_200_OK,
        )


class StudentMeView(generics.GenericAPIView):
    """Detailed current student context endpoint."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            student = (
                StudentProfile.objects.select_related(
                    "grade", "school", "education_level"
                )
                .prefetch_related(
                    "enrollments__course__subject",
                    "enrollments__course__teacher__user",
                )
                .get(user=user)
            )
        except StudentProfile.DoesNotExist as exc:
            raise PermissionDenied("No student profile found for this user.") from exc

        wallet = Wallet.objects.filter(user=user).first()
        enrollments = CourseEnrollment.objects.filter(student=student).select_related(
            "course__subject", "course__teacher__user", "course__grade"
        )

        return Response(
            {
                "user": UserSerializer(user).data,
                "profile": {
                    "id": str(student.id),
                    "birth_date": student.birth_date,
                    "grade": (
                        {"id": str(student.grade.id), "level": student.grade.level}
                        if student.grade
                        else None
                    ),
                    "education_level": (
                        {
                            "id": str(student.education_level.id),
                            "name": student.education_level.name,
                        }
                        if student.education_level
                        else None
                    ),
                    "school": (
                        {
                            "id": str(student.school.id),
                            "name": student.school.name,
                            "city": student.school.city,
                            "country": student.school.country,
                        }
                        if student.school
                        else None
                    ),
                },
                "wallet": (
                    {
                        "id": str(wallet.id),
                        "balance": str(wallet.balance.amount),
                        "currency": str(wallet.balance.currency),
                        "account_type": wallet.account_type,
                    }
                    if wallet
                    else None
                ),
                "subjects": sorted(
                    {
                        enrollment.course.subject.name
                        for enrollment in enrollments
                        if enrollment.course and enrollment.course.subject
                    }
                ),
                "courses": [
                    {
                        "id": str(enrollment.course.id),
                        "title": enrollment.course.title,
                        "subject": (
                            enrollment.course.subject.name
                            if enrollment.course.subject
                            else None
                        ),
                        "grade": (
                            enrollment.course.grade.level
                            if enrollment.course.grade
                            else None
                        ),
                        "teacher": (
                            f"{enrollment.course.teacher.user.first_name} {enrollment.course.teacher.user.last_name}".strip()
                            if enrollment.course.teacher
                            and enrollment.course.teacher.user
                            else None
                        ),
                        "is_active": enrollment.is_active,
                    }
                    for enrollment in enrollments
                    if enrollment.course
                ],
            },
            status=status.HTTP_200_OK,
        )


class ParentMeView(generics.GenericAPIView):
    """Detailed current parent context endpoint."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            parent = (
                ParentProfile.objects.select_related("user")
                .prefetch_related(
                    "children__user",
                    "children__grade",
                    "children__school",
                    "children__enrollments__course__subject",
                    "children__enrollments__course__teacher__user",
                )
                .get(user=user)
            )
        except ParentProfile.DoesNotExist as exc:
            raise PermissionDenied("No parent profile found for this user.") from exc

        wallet = Wallet.objects.filter(user=user).first()

        children_data = []
        for child in parent.children.all():
            enrollments = child.enrollments.select_related(
                "course__subject", "course__teacher__user", "course__grade"
            )
            children_data.append(
                {
                    "id": str(child.id),
                    "full_name": f"{child.user.first_name} {child.user.last_name}".strip(),
                    "email": child.user.email,
                    "birth_date": child.birth_date,
                    "grade": child.grade.level if child.grade else None,
                    "school": child.school.name if child.school else None,
                    "courses": [
                        {
                            "id": str(enrollment.course.id),
                            "title": enrollment.course.title,
                            "subject": (
                                enrollment.course.subject.name
                                if enrollment.course.subject
                                else None
                            ),
                            "teacher": (
                                f"{enrollment.course.teacher.user.first_name} {enrollment.course.teacher.user.last_name}".strip()
                                if enrollment.course.teacher
                                and enrollment.course.teacher.user
                                else None
                            ),
                            "is_active": enrollment.is_active,
                        }
                        for enrollment in enrollments
                        if enrollment.course
                    ],
                }
            )

        return Response(
            {
                "user": UserSerializer(user).data,
                "profile": {
                    "id": str(parent.id),
                    "birth_date": parent.birth_date,
                    "gender": parent.gender,
                    "national_identity_number": parent.national_identity_number,
                },
                "wallet": (
                    {
                        "id": str(wallet.id),
                        "balance": str(wallet.balance.amount),
                        "currency": str(wallet.balance.currency),
                        "account_type": wallet.account_type,
                    }
                    if wallet
                    else None
                ),
                "children": children_data,
            },
            status=status.HTTP_200_OK,
        )
