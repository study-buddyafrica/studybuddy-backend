from rest_framework import serializers
from apps.users.models import TeacherProfile
from apps.users.models import User 

class TeacherProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = TeacherProfile
        fields = [
            "id",
            "user",
            "email",
            "first_name",
            "last_name",
            "tsc_number",
            "tsc_number_certificate",
            "academic_certificate",
            "experience",
            "subjects",
            "id_number",
            "hourly_rate",
            "bio",
            "phone",
            "is_verified",
            "profile_picture",
            "birth_date",
            "gender",
            "grade",
        ]
        read_only_fields = ["is_verified", "user"]

    def validate(self, attrs):
        required_fields = [
            "tsc_number",
            "tsc_number_certificate",
            "academic_certificate",
            "experience",
            "subjects",
            "id_number",
            "hourly_rate",
        ]
        missing = [field for field in required_fields if not attrs.get(field)]
        if missing:
            raise serializers.ValidationError(
                {field: "This field is required." for field in missing}
            )
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        return TeacherProfile.objects.create(user=user, **validated_data)
