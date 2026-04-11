from datetime import date, datetime, timedelta
from decimal import Decimal
import requests

from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.files.base import ContentFile
from djmoney.money import Money
from django.utils import timezone

from apps.core.models import User
from apps.school.models import (
    School,
    Subject,
    Grade,
    Course,
    Topic,
    Subtopic,
    CourseEnrollment,
    SessionBooking,
    LiveSession,
    RevisionMaterial,
    Assessment,
    AssessmentSubmission,
    Question,
    Choice,
    SubtopicProgress,
    TopicProgress,
    CourseProgress,
)
from apps.users.models import (
    TeacherProfile,
    StudentProfile,
    ParentProfile,
    ParentChild,
    StudentLead,
    Availability,
    TeacherRating,
)
from apps.transactions.models import Wallet


class Command(BaseCommand):
    help = "Seed demo data for local development (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Maximum records to create per group (default: 5).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        limit = max(1, min(options["limit"], 5))

        self.stdout.write(self.style.NOTICE(f"Seeding demo data with limit={limit}"))

        grades = self._seed_grades(limit)
        subjects = self._seed_subjects(limit)
        schools = self._seed_schools(limit)

        teachers = self._seed_teachers(limit, schools, grades, subjects)
        students = self._seed_students(limit, schools, grades)
        parents = self._seed_parents(limit)
        self._seed_wallets(students, teachers, parents)

        self._link_parents_children(parents, students)
        courses = self._seed_courses(limit, subjects, grades, teachers)
        self._seed_enrollments_and_leads(courses, students)
        self._seed_session_bookings(courses, students, teachers)
        self._seed_topics_and_subtopics(limit, courses)
        self._seed_teacher_availability_and_ratings(teachers, students)
        self._seed_live_lessons(courses)
        self._seed_learning_artifacts(courses, students)

        self.stdout.write(self.style.SUCCESS("Seed complete."))

    def _ensure_demo_user_credentials(self, user, role):
        """Ensure seeded users can always authenticate with known credentials."""
        changed = False

        if user.role != role:
            user.role = role
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if not user.account_confirmed:
            user.account_confirmed = True
            changed = True

        # Always enforce known password for demo users.
        user.set_password("DemoPass123!")
        changed = True

        if changed:
            user.save()

    def _download_profile_picture(self, profile_obj, index):
        """Download and save a profile picture for seeded profiles."""
        # Profile picture URLs - using a pattern that returns different images
        urls = [
            "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSeb71XHQZlqHtJeBw1QVYXofy0XEFfD-nzZQ&s",  # Teacher 1
            "https://i.pravatar.cc/150?img=1",  # Teacher 2
            "https://i.pravatar.cc/150?img=2",  # Teacher 3
            "https://i.pravatar.cc/150?img=3",  # Teacher 4
            "https://i.pravatar.cc/150?img=4",  # Teacher 5
        ]
        
        try:
            url = urls[min(index - 1, len(urls) - 1)]
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            filename = f"profile_teacher_{index}.jpg"
            profile_obj.profile_picture.save(
                filename,
                ContentFile(response.content),
                save=True
            )
        except Exception as e:
            # Silently fail if download doesn't work (development environment)
            pass

    def _seed_grades(self, limit):
        level_values = [choice[0] for choice in Grade.GradeLevel.choices][:limit]
        created = []
        for level in level_values:
            grade, _ = Grade.objects.get_or_create(level=level)
            created.append(grade)
        self.stdout.write(self.style.SUCCESS(f"Grades: {len(created)} ready"))
        return created

    def _seed_subjects(self, limit):
        names = ["Mathematics", "English", "Biology", "Physics", "Chemistry"][:limit]
        created = []
        for idx, name in enumerate(names, start=1):
            subject, _ = Subject.objects.get_or_create(
                name=name,
                defaults={"description": f"{name} subject demo content #{idx}."},
            )
            created.append(subject)
        self.stdout.write(self.style.SUCCESS(f"Subjects: {len(created)} ready"))
        return created

    def _seed_schools(self, limit):
        created = []
        for idx in range(1, limit + 1):
            school, _ = School.objects.get_or_create(
                name=f"Demo School {idx}",
                defaults={
                    "address": f"Street {idx}",
                    "city": "Nairobi",
                    "contact": f"+2547000000{idx}",
                    "is_approved": True,
                },
            )
            created.append(school)
        self.stdout.write(self.style.SUCCESS(f"Schools: {len(created)} ready"))
        return created

    def _seed_teachers(self, limit, schools, grades, subjects):
        created = []
        for idx in range(1, limit + 1):
            email = f"teacher{idx}@studybuddy.demo"
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": f"Teacher{idx}",
                    "last_name": "Demo",
                    "username": f"teacher_demo_{idx}",
                    "role": "teacher",
                    "account_confirmed": True,
                    "is_active": True,
                },
            )
            self._ensure_demo_user_credentials(user, "teacher")

            teacher, _ = TeacherProfile.objects.get_or_create(
                user=user,
                defaults={
                    "experience": idx,
                    "hourly_rate": Decimal("500.00") + Decimal(str(idx * 50)),
                    "birth_date": date(1990, min(idx, 12), min(idx, 28)),
                    "is_verified": True,
                    "verification_status": "approved",
                    "school": schools[(idx - 1) % len(schools)] if schools else None,
                    "bio": f"Teacher demo profile {idx}.",
                    "phone": f"+254722000{idx:03d}",
                    "gender": "Male" if idx % 2 else "Female",
                    "teacher_license_number": f"TCH-DEMO-{idx:04d}",
                    "national_identity_number": f"ID-DEMO-{idx:06d}",
                },
            )

            changed = False
            if not teacher.teacher_license_number:
                teacher.teacher_license_number = f"TCH-DEMO-{idx:04d}"
                changed = True
            if not teacher.national_identity_number:
                teacher.national_identity_number = f"ID-DEMO-{idx:06d}"
                changed = True
            if not teacher.phone:
                teacher.phone = f"+254722000{idx:03d}"
                changed = True
            if not teacher.birth_date:
                teacher.birth_date = date(1990, min(idx, 12), min(idx, 28))
                changed = True
            if not teacher.hourly_rate:
                teacher.hourly_rate = Decimal("500.00") + Decimal(str(idx * 50))
                changed = True
            if not teacher.school_id and schools:
                teacher.school = schools[(idx - 1) % len(schools)]
                changed = True
            if teacher.verification_status != "approved":
                teacher.verification_status = "approved"
                changed = True
            if not teacher.is_verified:
                teacher.is_verified = True
                changed = True
            if changed:
                teacher.save()

            if grades:
                teacher.grade.set([grades[(idx - 1) % len(grades)]])
            if subjects:
                teacher.subjects.set([subjects[(idx - 1) % len(subjects)]])

            # Download and set profile picture
            if not teacher.profile_picture:
                self._download_profile_picture(teacher, idx)

            created.append(teacher)
        self.stdout.write(self.style.SUCCESS(f"Teachers: {len(created)} ready"))
        return created

    def _seed_students(self, limit, schools, grades):
        created = []
        for idx in range(1, limit + 1):
            email = f"student{idx}@studybuddy.demo"
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": f"Student{idx}",
                    "last_name": "Demo",
                    "username": f"student_demo_{idx}",
                    "role": "student",
                    "account_confirmed": True,
                    "is_active": True,
                },
            )
            self._ensure_demo_user_credentials(user, "student")

            student, _ = StudentProfile.objects.get_or_create(
                user=user,
                defaults={
                    "birth_date": date(2010, min(idx, 12), min(idx, 28)),
                    "grade": grades[(idx - 1) % len(grades)] if grades else None,
                    "school": schools[(idx - 1) % len(schools)] if schools else None,
                    "contact_name": f"Guardian {idx}",
                    "guardian_contact": f"+2547111111{idx}",
                },
            )
            created.append(student)
        self.stdout.write(self.style.SUCCESS(f"Students: {len(created)} ready"))
        return created

    def _seed_parents(self, limit):
        created = []
        for idx in range(1, limit + 1):
            email = f"parent{idx}@studybuddy.demo"
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": f"Parent{idx}",
                    "last_name": "Demo",
                    "username": f"parent_demo_{idx}",
                    "role": "parent",
                    "account_confirmed": True,
                    "is_active": True,
                },
            )
            self._ensure_demo_user_credentials(user, "parent")

            parent, _ = ParentProfile.objects.get_or_create(
                user=user,
                defaults={
                    "birth_date": date(1988, min(idx, 12), min(idx, 28)),
                },
            )
            created.append(parent)
        self.stdout.write(self.style.SUCCESS(f"Parents: {len(created)} ready"))
        return created

    def _link_parents_children(self, parents, students):
        links = 0
        if not parents or not students:
            self.stdout.write(self.style.WARNING("Parent-child links: 0 (insufficient profiles)"))
            return

        for idx, student in enumerate(students):
            parent = parents[idx % len(parents)]
            _, created = ParentChild.objects.get_or_create(parent=parent, child=student)
            if created:
                links += 1

        self.stdout.write(self.style.SUCCESS(f"Parent-child links: {links} created/ensured"))

    def _seed_courses(self, limit, subjects, grades, teachers):
        created = []
        if not subjects:
            self.stdout.write(self.style.WARNING("Courses: 0 (no subjects available)"))
            return created

        for idx in range(1, limit + 1):
            course, _ = Course.objects.get_or_create(
                title=f"Demo Course {idx}",
                defaults={
                    "subject": subjects[(idx - 1) % len(subjects)],
                    "grade": grades[(idx - 1) % len(grades)] if grades else None,
                    "description": f"Demo course description {idx}.",
                    "price": Decimal("1000.00") + Decimal(str(idx * 100)),
                    "teacher": teachers[(idx - 1) % len(teachers)] if teachers else None,
                    "is_universal": True,
                },
            )
            created.append(course)

        self.stdout.write(self.style.SUCCESS(f"Courses: {len(created)} ready"))
        return created

    def _seed_topics_and_subtopics(self, limit, courses):
        topics = 0
        subtopics = 0

        for idx, course in enumerate(courses, start=1):
            topic, topic_created = Topic.objects.get_or_create(
                course=course,
                title=f"Topic {idx}",
                defaults={
                    "order": idx,
                    "is_locked": False,
                    "description": f"Demo topic for {course.title}.",
                },
            )
            if topic_created:
                topics += 1

            _, sub_created = Subtopic.objects.get_or_create(
                topic=topic,
                title=f"Subtopic {idx}",
                defaults={
                    "order": 1,
                    "is_locked": False,
                    "content": f"Demo subtopic content for {course.title}.",
                },
            )
            if sub_created:
                subtopics += 1

        self.stdout.write(self.style.SUCCESS(f"Topics: {topics} created/ensured"))
        self.stdout.write(self.style.SUCCESS(f"Subtopics: {subtopics} created/ensured"))

    def _seed_teacher_availability_and_ratings(self, teachers, students):
        """Seed teacher availability slots and student reviews for teacher profiles."""
        if not teachers:
            self.stdout.write(self.style.WARNING("Availability/ratings: 0 (no teachers)"))
            return

        base = timezone.make_aware(datetime(2026, 1, 15, 9, 0, 0))
        availability_count = 0
        ratings_count = 0

        for idx, teacher in enumerate(teachers, start=1):
            for slot in range(2):
                start_time = base + timedelta(days=idx, hours=slot * 2)
                availability, created = Availability.objects.get_or_create(
                    teacher=teacher,
                    date=start_time,
                    defaults={
                        "end_date": start_time + timedelta(hours=1),
                        "is_blocked": False,
                    },
                )
                if availability.end_date is None:
                    availability.end_date = start_time + timedelta(hours=1)
                    availability.save(update_fields=["end_date"])
                if created:
                    availability_count += 1

            if not students:
                continue

            for offset in range(min(2, len(students))):
                student = students[(idx + offset - 1) % len(students)]
                rating_value = 4 + ((idx + offset) % 2)
                rating, created = TeacherRating.objects.get_or_create(
                    teacher=teacher,
                    student=student,
                    defaults={"rating": rating_value},
                )
                if rating.rating != rating_value:
                    rating.rating = rating_value
                    rating.save(update_fields=["rating"])
                if created:
                    ratings_count += 1

        self.stdout.write(self.style.SUCCESS(f"Availability slots: {availability_count} created/ensured"))
        self.stdout.write(self.style.SUCCESS(f"Teacher ratings: {ratings_count} created/ensured"))

    def _seed_live_lessons(self, courses):
        """Seed live lesson records from accepted bookings for teacher dashboards."""
        bookings = SessionBooking.objects.filter(status="accepted").select_related(
            "teacher__user", "student__user", "course"
        )

        if not bookings.exists():
            self.stdout.write(self.style.WARNING("Live lessons: 0 (no accepted bookings)"))
            return

        created = 0
        for booking in bookings:
            course = booking.course or (courses[0] if courses else None)
            room_key = str(booking.id).replace("-", "")[:12]

            _, was_created = LiveSession.objects.get_or_create(
                session=booking,
                defaults={
                    "teacher": booking.teacher,
                    "course": course,
                    "title": f"{course.title if course else 'Demo'} Live Session",
                    "description": f"Live class for booking {booking.id}.",
                    "started_at": booking.scheduled_start,
                    "ended_at": booking.scheduled_end,
                    "teacher_meeting_link": f"https://mock.daily.co/{room_key}-teacher",
                    "student_meeting_link": f"https://mock.daily.co/{room_key}-student",
                    "whiteboard_link": "https://excalidraw.com/",
                },
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Live lessons: {created} created/ensured"))

    def _seed_learning_artifacts(self, courses, students):
        """Seed revision materials, assessments, submissions, and progress records."""
        if not courses:
            self.stdout.write(self.style.WARNING("Learning artifacts: 0 (no courses)"))
            return

        materials = 0
        assessments = 0
        questions = 0
        submissions = 0
        progress_rows = 0
        due_base = timezone.now() + timedelta(days=7)

        for idx, course in enumerate(courses, start=1):
            teacher = course.teacher
            if teacher is None:
                continue

            _, mat_created = RevisionMaterial.objects.get_or_create(
                title=f"{course.title} Revision Pack",
                course=course,
                uploaded_by=teacher,
                defaults={
                    "description": f"Revision material for {course.title}.",
                },
            )
            if mat_created:
                materials += 1

            assessment, ass_created = Assessment.objects.get_or_create(
                title=f"{course.title} Weekly Quiz",
                course=course,
                teacher=teacher,
                defaults={
                    "description": f"Auto-seeded quiz for {course.title}.",
                    "due_date": due_base + timedelta(days=idx),
                    "max_score": 100,
                    "assessment_type": "mcq",
                },
            )
            if ass_created:
                assessments += 1

            question, q_created = Question.objects.get_or_create(
                assessment=assessment,
                order=1,
                defaults={
                    "text": f"What is the key concept in {course.title}?",
                    "points": 5,
                },
            )
            if q_created:
                questions += 1

            Choice.objects.get_or_create(
                question=question,
                text="Concept A",
                defaults={"is_correct": True},
            )
            Choice.objects.get_or_create(
                question=question,
                text="Concept B",
                defaults={"is_correct": False},
            )

            enrolled = list(
                CourseEnrollment.objects.filter(course=course, is_active=True)
                .select_related("student__user")[:2]
            )

            for row in enrolled:
                submission, sub_created = AssessmentSubmission.objects.get_or_create(
                    assessment=assessment,
                    student=row.student,
                    defaults={
                        "answers": {"q1": "Concept A"},
                        "grading": 80.0,
                        "feedback": "Good attempt.",
                        "status": "graded",
                    },
                )
                if submission.status != "graded":
                    submission.status = "graded"
                    submission.save(update_fields=["status"])
                if sub_created:
                    submissions += 1

                first_topic = Topic.objects.filter(course=course).order_by("order", "created_at").first()
                if first_topic:
                    _, created = TopicProgress.objects.get_or_create(
                        student=row.student,
                        topic=first_topic,
                        defaults={
                            "is_complete": True,
                            "completed_at": timezone.now() - timedelta(days=1),
                        },
                    )
                    if created:
                        progress_rows += 1

                    first_subtopic = (
                        Subtopic.objects.filter(topic=first_topic).order_by("order", "created_at").first()
                    )
                    if first_subtopic:
                        _, created = SubtopicProgress.objects.get_or_create(
                            student=row.student,
                            subtopic=first_subtopic,
                            defaults={
                                "is_complete": True,
                                "completed_at": timezone.now() - timedelta(days=1),
                            },
                        )
                        if created:
                            progress_rows += 1

                _, created = CourseProgress.objects.get_or_create(
                    student=row.student,
                    course=course,
                    defaults={
                        "is_complete": False,
                    },
                )
                if created:
                    progress_rows += 1

        self.stdout.write(self.style.SUCCESS(f"Revision materials: {materials} created/ensured"))
        self.stdout.write(self.style.SUCCESS(f"Assessments: {assessments} created/ensured"))
        self.stdout.write(self.style.SUCCESS(f"Assessment questions: {questions} created/ensured"))
        self.stdout.write(self.style.SUCCESS(f"Assessment submissions: {submissions} created/ensured"))
        self.stdout.write(self.style.SUCCESS(f"Progress rows: {progress_rows} created/ensured"))

    def _seed_enrollments_and_leads(self, courses, students):
        """Create active enrollments and designate a lead student per course."""
        if not courses or not students:
            self.stdout.write(self.style.WARNING("Enrollments/leads: 0 (insufficient data)"))
            return

        enrollments = 0
        leads = 0

        for idx, course in enumerate(courses):
            lead_student = students[idx % len(students)]

            enrolled_students = []
            for offset in range(min(3, len(students))):
                student = students[(idx + offset) % len(students)]
                enrollment, created = CourseEnrollment.objects.get_or_create(
                    course=course,
                    student=student,
                    defaults={"is_active": True},
                )
                if not enrollment.is_active:
                    enrollment.is_active = True
                    enrollment.save(update_fields=["is_active"])
                if created:
                    enrollments += 1
                enrolled_students.append(student)

            if lead_student not in enrolled_students:
                enrolled_students.append(lead_student)

            lead, lead_created = StudentLead.objects.get_or_create(
                course=course,
                student_profile=lead_student,
                defaults={"is_a_lead": True},
            )
            if not lead.is_a_lead:
                lead.is_a_lead = True
                lead.save(update_fields=["is_a_lead"])
            if lead_created:
                leads += 1

        self.stdout.write(self.style.SUCCESS(f"Enrollments: {enrollments} created/ensured"))
        self.stdout.write(self.style.SUCCESS(f"Course leads: {leads} created/ensured"))

    def _seed_wallets(self, students, teachers, parents):
        """Ensure wallets exist and are funded for all key actors in local testing."""
        system_user, _ = User.objects.get_or_create(
            email="system@studybuddy.demo",
            defaults={
                "first_name": "System",
                "last_name": "Account",
                "username": "system_demo",
                "is_superuser": True,
                "is_staff": True,
                "is_active": True,
                "account_confirmed": True,
            },
        )

        system_user.is_superuser = True
        system_user.is_staff = True
        system_user.is_active = True
        system_user.account_confirmed = True
        system_user.set_password("DemoPass123!")
        system_user.save()

        system_wallet, _ = Wallet.objects.get_or_create(
            user=system_user,
            defaults={
                "account_type": "system",
                "failed_withdraw_attempts": 0,
                "balance": Money(0, "KES"),
            },
        )

        if system_wallet.account_type != "system":
            system_wallet.account_type = "system"

        if system_wallet.balance < Money(200000, "KES"):
            system_wallet.balance = Money(200000, "KES")
        system_wallet.save()

        funded = {"student": 0, "teacher": 0, "parent": 0}

        for student in students:
            wallet, _ = Wallet.objects.get_or_create(
                user=student.user,
                defaults={
                    "account_type": "student",
                    "failed_withdraw_attempts": 0,
                    "balance": Money(0, "KES"),
                },
            )
            wallet.account_type = "student"
            if wallet.balance < Money(10000, "KES"):
                wallet.balance = Money(10000, "KES")
                funded["student"] += 1
            wallet.save()

        for teacher in teachers:
            wallet, _ = Wallet.objects.get_or_create(
                user=teacher.user,
                defaults={
                    "account_type": "teacher",
                    "failed_withdraw_attempts": 0,
                    "balance": Money(0, "KES"),
                },
            )
            wallet.account_type = "teacher"
            if wallet.balance < Money(2000, "KES"):
                wallet.balance = Money(2000, "KES")
                funded["teacher"] += 1
            wallet.save()

        for parent in parents:
            wallet, _ = Wallet.objects.get_or_create(
                user=parent.user,
                defaults={
                    "account_type": "parent",
                    "failed_withdraw_attempts": 0,
                    "balance": Money(0, "KES"),
                },
            )
            wallet.account_type = "parent"
            if wallet.balance < Money(15000, "KES"):
                wallet.balance = Money(15000, "KES")
                funded["parent"] += 1
            wallet.save()

        self.stdout.write(self.style.SUCCESS("System wallet: ensured and funded"))
        self.stdout.write(self.style.SUCCESS(f"Student wallets funded/updated: {funded['student']}"))
        self.stdout.write(self.style.SUCCESS(f"Teacher wallets funded/updated: {funded['teacher']}"))
        self.stdout.write(self.style.SUCCESS(f"Parent wallets funded/updated: {funded['parent']}"))

    def _seed_session_bookings(self, courses, students, teachers):
        """Create accepted bookings so teacher live-session dropdown has data."""
        if not courses or not students or not teachers:
            self.stdout.write(self.style.WARNING("Session bookings: 0 (insufficient data)"))
            return

        created = 0
        now = timezone.now()
        for idx in range(min(len(students), len(teachers), 5)):
            course = courses[idx % len(courses)]
            student = students[idx % len(students)]
            teacher = teachers[idx % len(teachers)]

            booking, was_created = SessionBooking.objects.get_or_create(
                student=student,
                teacher=teacher,
                scheduled_start=now + timezone.timedelta(days=idx + 1),
                defaults={
                    "scheduled_end": now + timezone.timedelta(days=idx + 1, hours=1),
                    "status": "accepted",
                    "is_allowed": True,
                    "cost": Decimal("750.00"),
                    "course": course,
                },
            )

            # Keep existing records usable for dropdown if already present.
            changed = False
            if booking.status != "accepted":
                booking.status = "accepted"
                changed = True
            if not booking.is_allowed:
                booking.is_allowed = True
                changed = True
            if booking.course_id is None:
                booking.course = course
                changed = True
            if changed:
                booking.save()

            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Session bookings accepted/ensured: {created}"))
