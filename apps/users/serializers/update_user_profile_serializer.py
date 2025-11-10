from rest_framework import serializers
from apps.users.models import TeacherProfile, StudentProfile,ParentChild,ParentProfile

class TeacherProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherProfile
        fields = [
            "bio",
            "phone",
            "hourly_rate",
            "subjects",
            "grade",
            "experience",
            "profile_picture",
        ]
        read_only_fields = ["id", "user", "is_verified", "tsc_number"]

    def update(self, instance, validated_data):
        # Clean handling of many-to-many updates
        subjects = validated_data.pop("subjects", None)
        grades = validated_data.pop("grade", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if subjects is not None:
            instance.subjects.set(subjects)

        if grades is not None:
            instance.grade.set(grades)

        instance.save()
        return instance
    

class StudentProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = [
            "profile_picture",
            "birth_date",
            "contact_name",
            "guardian_contact",
            "grade",
            "school",
            "subjects",
        ]
        read_only_fields = ["id", "user", "enrollment_date"]

    def update(self, instance, validated_data):
        subjects = validated_data.pop("subjects", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if subjects is not None:
            instance.subjects.set(subjects)

        instance.save()
        return instance


class ParentProfileUpdateSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ParentProfile
        fields = [
            "profile_picture",
            "birth_date",
            "full_name",
        ]
        read_only_fields = ["id", "user", "children", "full_name"]

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()


