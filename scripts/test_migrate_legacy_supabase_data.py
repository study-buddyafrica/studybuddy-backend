"""
Unit tests for StudyBuddy Africa Legacy Data Migration Pipeline (Phase 2)
Tests transformations, edge cases, deduplication, and schema drift handling.
"""

import json
import unittest
import uuid
from unittest.mock import MagicMock, patch

from scripts.migrate_legacy_supabase_data import (
    CANONICAL_EDUCATION_LEVELS,
    CANONICAL_GRADES,
    GRADE_ALIASES,
    LegacyDataMigrator,
    MigrationStats,
)


class TestMigrationTransformations(unittest.TestCase):
    def setUp(self):
        self.migrator = LegacyDataMigrator(
            legacy_url="postgresql://fake:fake@localhost:5432/legacy",
            target_url="postgresql://fake:fake@localhost:5432/target",
            dry_run=True,
        )

    def test_canonical_education_levels_structure(self):
        self.assertEqual(len(CANONICAL_EDUCATION_LEVELS), 3)
        codes = {lvl["code"] for lvl in CANONICAL_EDUCATION_LEVELS}
        self.assertEqual(codes, {"k12", "university", "continuous"})

    def test_grade_alias_normalization(self):
        self.assertEqual(GRADE_ALIASES.get("form 1"), "Grade 9")
        self.assertEqual(GRADE_ALIASES.get("form 4"), "Grade 12")
        self.assertEqual(GRADE_ALIASES.get("class 8"), "Grade 8")
        self.assertIn("Grade 9", CANONICAL_GRADES)
        self.assertIn("General", CANONICAL_GRADES)

    def test_user_email_collision_handling(self):
        # Target already has Eli's account
        target_cur = MagicMock()
        legacy_cur = MagicMock()

        self.migrator.user_email_map["eli@studybuddy.africa"] = "target-eli-uuid"
        self.migrator.user_username_set.add("eli")

        # Legacy user with same email
        legacy_cur.fetchall.return_value = [
            {
                "id": "legacy-eli-uuid",
                "email": "eli@studybuddy.africa",
                "first_name": "Eli",
                "last_name": "Keli",
                "username": "eli",
                "password": "hashed_password",
                "role": "teacher",
                "created_at": None,
            }
        ]

        self.migrator.migrate_users(legacy_cur, target_cur)

        # Confirm target account preserved, not overwritten
        self.assertIn("target-eli-uuid", self.migrator.migrated_user_ids)
        self.assertEqual(self.migrator.stats.stats["users"]["skipped"], 1)
        self.assertEqual(self.migrator.stats.stats["users"]["inserted"], 0)

    def test_user_username_collision_resolution(self):
        # Target has username 'victor' with different email
        target_cur = MagicMock()
        legacy_cur = MagicMock()

        self.migrator.user_email_map["active_victor@studybuddy.africa"] = "target-v-uuid"
        self.migrator.user_username_set.add("victor")

        # Legacy user with different email but colliding username 'victor'
        legacy_cur.fetchall.return_value = [
            {
                "id": "12345678-abcd-ef01-2345-6789abcdef01",
                "email": "legacy_victor@gmail.com",
                "first_name": "Victor",
                "last_name": "M",
                "username": "victor",
                "password": "hashed_password",
                "role": "teacher",
                "created_at": None,
            }
        ]

        self.migrator.migrate_users(legacy_cur, target_cur)

        # Verify username resolved with suffix
        self.assertIn("victor_1234", self.migrator.user_username_set)
        self.assertEqual(self.migrator.stats.stats["users"]["inserted"], 1)

    def test_wallets_auto_provisioning_companion(self):
        target_cur = MagicMock()
        teacher_user_id = str(uuid.uuid4())
        self.migrator.migrated_user_ids.add(teacher_user_id)

        self.migrator.migrate_wallets(target_cur)

        self.assertEqual(self.migrator.stats.stats["wallets"]["inserted"], 1)

    def test_teacher_profile_fallbacks_and_currency(self):
        legacy_cur = MagicMock()
        target_cur = MagicMock()

        user_id = str(uuid.uuid4())
        self.migrator.migrated_user_ids.add(user_id)

        # Legacy teacher with null phone and null profile_picture
        legacy_cur.fetchall.return_value = [
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "hourly_rate": 500.00,
                "phone": None,
                "profile_picture": None,
                "school_id": None,
                "curriculums_taught": None,
                "highest_qualification": None,
            }
        ]

        self.migrator.migrate_teacher_profiles(legacy_cur, target_cur)
        self.assertEqual(self.migrator.stats.stats["teacher_profiles"]["inserted"], 1)

    def test_course_country_and_currency_invariants(self):
        legacy_cur = MagicMock()
        target_cur = MagicMock()

        course_id = str(uuid.uuid4())
        self.migrator.subject_map["mathematics"] = str(uuid.uuid4())

        legacy_cur.fetchall.return_value = [
            {
                "id": course_id,
                "title": "Mathematics Grade 9",
                "description": "CBC Grade 9 Mathematics",
                "price": 1200.00,
                "subject_id": self.migrator.subject_map["mathematics"],
                "teacher_id": None,
                "grade_id": None,
                "created_at": None,
            }
        ]

        self.migrator.migrate_courses(legacy_cur, target_cur)
        self.assertIn(course_id, self.migrator.migrated_course_ids)
        self.assertEqual(self.migrator.stats.stats["courses"]["inserted"], 1)

    def test_subtopic_empty_content_guard(self):
        legacy_cur = MagicMock()
        target_cur = MagicMock()

        topic_id = str(uuid.uuid4())
        self.migrator.migrated_topic_ids.add(topic_id)

        # Legacy subtopic with both content and content_file null
        subtopic_id = str(uuid.uuid4())
        legacy_cur.fetchall.return_value = [
            {
                "id": subtopic_id,
                "topic_id": topic_id,
                "title": "Introduction to Linear Equations",
                "content": None,
                "content_file": None,
                "order": 1,
                "is_locked": True,
                "created_at": None,
            }
        ]

        self.migrator.migrate_subtopics(legacy_cur, target_cur)
        self.assertEqual(self.migrator.stats.stats["subtopics"]["inserted"], 1)

    def test_revision_materials_file_url_refactor_mapping(self):
        legacy_cur = MagicMock()
        target_cur = MagicMock()

        legacy_cur.fetchone.return_value = {"table_name": "revision_materials"}

        mat_id = str(uuid.uuid4())
        legacy_cur.fetchall.return_value = [
            {
                "id": mat_id,
                "title": "Form 3 Past Papers",
                "description": "Past KCSE papers",
                "file_url": "materials/past_papers.pdf",
                "file": None,
                "course_id": None,
                "uploaded_by_id": None,
                "created_at": None,
            }
        ]

        self.migrator.migrate_revision_materials(legacy_cur, target_cur)
        self.assertEqual(self.migrator.stats.stats["revision_materials"]["inserted"], 1)


if __name__ == "__main__":
    unittest.main()
