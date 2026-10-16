#!/usr/bin/env python3
"""
StudyBuddy Africa — Legacy Supabase Data Migration ETL Pipeline (Phase 2)
Author: Forge (Lead Software Engineer & System Architect)
Governance: /Users/mac/Knowledge/Obsidian/Hermes-STUDYBUDDY/Forge-Onboarding/forge-studybuddy-onboarding-boundary.md
Architecture Blueprint: Docs/Architecture/Backend-Database-Schema-and-Relationships.md
Inventory Reference: Repo-Notes/legacy-supabase-migration-inventory.md

This script performs an idempotent, fail-closed ETL extraction from the legacy 2025
Supabase database into the active dedicated PostgreSQL 17 database (yhdwspntnazxhipmxggs).

Execution DAG Sequence (13 Steps):
 1. education_levels (ensure canonical tiers: k12, university, continuous)
 2. grades (normalize level labels)
 3. subjects (case-insensitive deduplication)
 4. schools (institution catalogs)
 5. users (filtered by role = 'teacher'; inject onboarding_step = 'completed', account_confirmed = true)
 6. wallets (auto-provision 1:1 companion wallet: failed_withdraw_attempts = 0, is_active = True, KES)
 7. teacher_profiles (hourly_rate_currency = 'KES', is_verified = True, phone/avatar fallbacks)
 8. teacher_profiles_grade (M2M junction)
 9. teacher_profiles_subjects (M2M junction)
 10. courses (country = 'Kenya', is_universal = False, price_currency = 'KES')
 11. topics (preserve order, UUIDs)
 12. subtopics (content fallback if both content and content_file are null)
 13. revision_materials (map legacy file_url -> file)

Usage:
  python scripts/migrate_legacy_supabase_data.py --dry-run
  python scripts/migrate_legacy_supabase_data.py --legacy-url "postgresql://..." --target-url "postgresql://..."
"""

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("sba_migration")

# Canonical Education Levels
CANONICAL_EDUCATION_LEVELS = [
    {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "code": "k12",
        "name": "K-12 Education",
        "description": "Primary and Secondary Curriculum",
    },
    {
        "id": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
        "code": "university",
        "name": "University & Higher Ed",
        "description": "Undergraduate and Polytechnic Courses",
    },
    {
        "id": "c3d4e5f6-a7b8-9012-cdef-345678901234",
        "code": "continuous",
        "name": "Continuous Learning",
        "description": "Professional Skills and Adult Education",
    },
]

# Canonical Grade Levels
CANONICAL_GRADES = [
    "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6",
    "Grade 7", "Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12",
    "College", "University", "Professional", "General"
]

GRADE_ALIASES = {
    "form 1": "Grade 9",
    "form 2": "Grade 10",
    "form 3": "Grade 11",
    "form 4": "Grade 12",
    "class 1": "Grade 1",
    "class 2": "Grade 2",
    "class 3": "Grade 3",
    "class 4": "Grade 4",
    "class 5": "Grade 5",
    "class 6": "Grade 6",
    "class 7": "Grade 7",
    "class 8": "Grade 8",
}


class MigrationStats:
    def __init__(self):
        self.stats: Dict[str, Dict[str, int]] = {}

    def init_table(self, table: str):
        self.stats[table] = {
            "extracted": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "quarantined": 0,
        }

    def increment(self, table: str, key: str, count: int = 1):
        if table not in self.stats:
            self.init_table(table)
        self.stats[table][key] += count

    def print_summary(self):
        logger.info("\n" + "=" * 80)
        logger.info("MIGRATION EXECUTION SUMMARY MATRIX")
        logger.info("=" * 80)
        header = f"{'Step':<4} | {'Table':<26} | {'Extracted':<9} | {'Inserted':<8} | {'Updated':<7} | {'Quarantine':<10}"
        logger.info(header)
        logger.info("-" * 80)
        for idx, (tbl, s) in enumerate(self.stats.items(), 1):
            logger.info(
                f"{idx:<4} | {tbl:<26} | {s['extracted']:<9} | {s['inserted']:<8} | {s['updated']:<7} | {s['quarantined']:<10}"
            )
        logger.info("=" * 80 + "\n")


class LegacyDataMigrator:
    def __init__(
        self,
        legacy_url: str,
        target_url: str,
        dry_run: bool = False,
        batch_size: int = 100,
        quarantine_file: Optional[str] = None,
    ):
        self.legacy_url = legacy_url
        self.target_url = target_url
        self.dry_run = dry_run
        self.batch_size = batch_size
        self.quarantine_file = quarantine_file or f"migration_quarantine_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.stats = MigrationStats()
        self.quarantined_records: List[Dict[str, Any]] = []

        # In-memory ID resolution caches
        self.education_level_map: Dict[str, str] = {}  # code -> id
        self.grade_map: Dict[str, str] = {}  # level -> id
        self.subject_map: Dict[str, str] = {}  # lower(name) -> id
        self.school_ids: Set[str] = set()
        self.user_email_map: Dict[str, str] = {}  # email -> id
        self.user_username_set: Set[str] = set()
        self.migrated_user_ids: Set[str] = set()
        self.migrated_teacher_ids: Set[str] = set()
        self.migrated_course_ids: Set[str] = set()
        self.migrated_topic_ids: Set[str] = set()

    def connect_db(self, url: str, read_only: bool = False):
        try:
            conn = psycopg2.connect(url)
            if read_only:
                conn.set_session(readonly=True, autocommit=True)
            else:
                conn.autocommit = False
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database ({'read-only' if read_only else 'target'}): {e}")
            raise

    def quarantine(self, table: str, row_id: Any, reason: str, data: Any):
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "table": table,
            "row_id": str(row_id),
            "reason": reason,
            "data": data,
        }
        self.quarantined_records.append(record)
        self.stats.increment(table, "quarantined")
        logger.warning(f"[{table}] Quarantined row {row_id}: {reason}")

    def save_quarantine_report(self):
        if self.quarantined_records:
            with open(self.quarantine_file, "w") as f:
                json.dump(self.quarantined_records, f, indent=2, default=str)
            logger.info(f"Quarantine log saved to {self.quarantine_file} ({len(self.quarantined_records)} records)")

    # ---------------------------------------------------------
    # Pre-flight Caches & Target State Discovery
    # ---------------------------------------------------------
    def load_target_caches(self, target_cur):
        logger.info("Discovering target database state and populating resolution caches...")

        # Existing education levels
        target_cur.execute("SELECT id, code FROM education_levels;")
        for row in target_cur.fetchall():
            self.education_level_map[row["code"]] = str(row["id"])

        # Existing grades
        target_cur.execute("SELECT id, level FROM grades;")
        for row in target_cur.fetchall():
            self.grade_map[row["level"]] = str(row["id"])

        # Existing subjects
        target_cur.execute("SELECT id, name FROM subjects;")
        for row in target_cur.fetchall():
            self.subject_map[row["name"].strip().lower()] = str(row["id"])

        # Existing schools
        target_cur.execute("SELECT id FROM schools;")
        for row in target_cur.fetchall():
            self.school_ids.add(str(row["id"]))

        # Existing users
        target_cur.execute("SELECT id, email, username FROM users;")
        for row in target_cur.fetchall():
            self.user_email_map[row["email"].strip().lower()] = str(row["id"])
            self.user_username_set.add(row["username"].strip().lower())

        logger.info(
            f"Pre-flight cache ready: {len(self.education_level_map)} ed levels, {len(self.grade_map)} grades, "
            f"{len(self.subject_map)} subjects, {len(self.user_email_map)} users."
        )

    # ---------------------------------------------------------
    # Step 1: Education Levels
    # ---------------------------------------------------------
    def migrate_education_levels(self, target_cur):
        table = "education_levels"
        self.stats.init_table(table)
        logger.info("Step 1/13: Seeding canonical education_levels...")

        for lvl in CANONICAL_EDUCATION_LEVELS:
            self.stats.increment(table, "extracted")
            if lvl["code"] in self.education_level_map:
                self.stats.increment(table, "skipped")
                continue

            lvl_id = lvl["id"]
            if not self.dry_run:
                target_cur.execute(
                    """
                    INSERT INTO education_levels (id, code, name, description, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (code) DO NOTHING
                    RETURNING id;
                    """,
                    (lvl_id, lvl["code"], lvl["name"], lvl["description"]),
                )
                res = target_cur.fetchone()
                if res:
                    self.education_level_map[lvl["code"]] = str(res["id"])
                    self.stats.increment(table, "inserted")
                else:
                    self.stats.increment(table, "skipped")
            else:
                self.education_level_map[lvl["code"]] = lvl_id
                self.stats.increment(table, "inserted")

    # ---------------------------------------------------------
    # Step 2: Grades
    # ---------------------------------------------------------
    def migrate_grades(self, legacy_cur, target_cur):
        table = "grades"
        self.stats.init_table(table)
        logger.info("Step 2/13: Migrating and normalizing academic grades...")

        legacy_cur.execute("SELECT id, level, created_at, updated_at FROM grades;")
        legacy_rows = legacy_cur.fetchall()

        for row in legacy_rows:
            self.stats.increment(table, "extracted")
            raw_level = (row.get("level") or "").strip()
            norm_level = GRADE_ALIASES.get(raw_level.lower(), raw_level)

            if norm_level not in CANONICAL_GRADES:
                norm_level = "General"

            grade_id = str(row["id"])
            if norm_level in self.grade_map:
                self.grade_map[norm_level] = self.grade_map[norm_level]
                self.stats.increment(table, "skipped")
                continue

            if not self.dry_run:
                target_cur.execute(
                    """
                    INSERT INTO grades (id, level, created_at, updated_at)
                    VALUES (%s, %s, COALESCE(%s, NOW()), NOW())
                    ON CONFLICT (level) DO NOTHING
                    RETURNING id;
                    """,
                    (grade_id, norm_level, row.get("created_at")),
                )
                res = target_cur.fetchone()
                if res:
                    self.grade_map[norm_level] = str(res["id"])
                    self.stats.increment(table, "inserted")
                else:
                    self.stats.increment(table, "skipped")
            else:
                self.grade_map[norm_level] = grade_id
                self.stats.increment(table, "inserted")

    # ---------------------------------------------------------
    # Step 3: Subjects
    # ---------------------------------------------------------
    def migrate_subjects(self, legacy_cur, target_cur):
        table = "subjects"
        self.stats.init_table(table)
        logger.info("Step 3/13: Migrating subjects with case-insensitive deduplication...")

        legacy_cur.execute("SELECT id, name, description, created_at, updated_at FROM subjects;")
        legacy_rows = legacy_cur.fetchall()

        for row in legacy_rows:
            self.stats.increment(table, "extracted")
            name = (row.get("name") or "").strip()
            if not name:
                self.quarantine(table, row.get("id"), "Subject name is empty", row)
                continue

            clean_key = name.lower()
            subject_id = str(row["id"])

            if clean_key in self.subject_map:
                self.stats.increment(table, "skipped")
                continue

            if not self.dry_run:
                target_cur.execute(
                    """
                    INSERT INTO subjects (id, name, description, created_at, updated_at)
                    VALUES (%s, %s, %s, COALESCE(%s, NOW()), NOW())
                    ON CONFLICT (id) DO UPDATE SET
                      name = EXCLUDED.name,
                      description = COALESCE(EXCLUDED.description, subjects.description),
                      updated_at = NOW()
                    RETURNING id;
                    """,
                    (subject_id, name, row.get("description"), row.get("created_at")),
                )
                self.subject_map[clean_key] = subject_id
                self.stats.increment(table, "inserted")
            else:
                self.subject_map[clean_key] = subject_id
                self.stats.increment(table, "inserted")

    # ---------------------------------------------------------
    # Step 4: Schools
    # ---------------------------------------------------------
    def migrate_schools(self, legacy_cur, target_cur):
        table = "schools"
        self.stats.init_table(table)
        logger.info("Step 4/13: Migrating schools and institutional catalogs...")

        legacy_cur.execute("SELECT * FROM schools;")
        legacy_rows = legacy_cur.fetchall()

        for row in legacy_rows:
            self.stats.increment(table, "extracted")
            school_id = str(row["id"])
            name = (row.get("name") or "").strip()
            if not name:
                self.quarantine(table, school_id, "School name is empty", row)
                continue

            address = (row.get("address") or "Nairobi").strip()
            city = (row.get("city") or "Nairobi").strip()
            country = "Kenya"
            contact = (row.get("contact") or "+254700000000").strip()

            if not self.dry_run:
                target_cur.execute(
                    """
                    INSERT INTO schools (id, name, address, city, country, contact, is_approved, created_by_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, True, NULL, COALESCE(%s, NOW()), NOW())
                    ON CONFLICT (id) DO UPDATE SET
                      name = EXCLUDED.name,
                      updated_at = NOW();
                    """,
                    (school_id, name, address, city, country, contact, row.get("created_at")),
                )
                self.school_ids.add(school_id)
                self.stats.increment(table, "inserted")
            else:
                self.school_ids.add(school_id)
                self.stats.increment(table, "inserted")

    # ---------------------------------------------------------
    # Step 5: Users (Teachers Only)
    # ---------------------------------------------------------
    def migrate_users(self, legacy_cur, target_cur):
        table = "users"
        self.stats.init_table(table)
        logger.info("Step 5/13: Migrating verified educators (role = 'teacher')...")

        legacy_cur.execute(
            """
            SELECT id, email, first_name, last_name, username, password, role,
                   is_active, is_staff, is_superuser, account_confirmed, created_at, updated_at
            FROM users
            WHERE role = 'teacher';
            """
        )
        legacy_rows = legacy_cur.fetchall()

        for row in legacy_rows:
            self.stats.increment(table, "extracted")
            legacy_id = str(row["id"])
            email = (row.get("email") or "").strip().lower()

            if not email:
                self.quarantine(table, legacy_id, "Teacher email is empty", row)
                continue

            first_name = (row.get("first_name") or "Educator").strip()
            last_name = (row.get("last_name") or "").strip()
            raw_username = (row.get("username") or email.split("@")[0]).strip()
            password = row.get("password") or "!UNUSABLE_PASSWORD"

            # Check for email collision with active DB (Eli, Faith, test records)
            if email in self.user_email_map:
                existing_target_id = self.user_email_map[email]
                logger.info(f"User email collision: {email} exists in target as {existing_target_id}. Preserving target account.")
                self.migrated_user_ids.add(existing_target_id)
                self.stats.increment(table, "skipped")
                continue

            # Check for username collision on different email
            username = raw_username
            if username.lower() in self.user_username_set:
                suffix = f"_{legacy_id[:4]}"
                username = f"{raw_username[:25]}{suffix}"
                logger.info(f"Username collision resolved: {raw_username} -> {username}")

            if not self.dry_run:
                target_cur.execute(
                    """
                    INSERT INTO users (
                      id, email, first_name, last_name, username, password, role,
                      is_active, is_staff, is_superuser, account_confirmed,
                      onboarding_step, country, created_at, updated_at
                    ) VALUES (
                      %s, %s, %s, %s, %s, %s, 'teacher',
                      True, False, False, True,
                      'completed', 'Kenya', COALESCE(%s, NOW()), NOW()
                    )
                    ON CONFLICT (email) DO UPDATE SET
                      role = 'teacher',
                      account_confirmed = True,
                      onboarding_step = 'completed',
                      updated_at = NOW()
                    RETURNING id;
                    """,
                    (legacy_id, email, first_name, last_name, username, password, row.get("created_at")),
                )
                res = target_cur.fetchone()
                target_user_id = str(res["id"])
                self.user_email_map[email] = target_user_id
                self.user_username_set.add(username.lower())
                self.migrated_user_ids.add(target_user_id)
                self.stats.increment(table, "inserted")
            else:
                self.user_email_map[email] = legacy_id
                self.user_username_set.add(username.lower())
                self.migrated_user_ids.add(legacy_id)
                self.stats.increment(table, "inserted")

    # ---------------------------------------------------------
    # Step 6: Wallets (Auto-Provisioned Companion)
    # ---------------------------------------------------------
    def migrate_wallets(self, target_cur):
        table = "wallets"
        self.stats.init_table(table)
        logger.info("Step 6/13: Auto-provisioning FinTech companion wallets (1:1 with teachers)...")

        for user_id in self.migrated_user_ids:
            self.stats.increment(table, "extracted")
            wallet_id = str(uuid.uuid4())
            wallet_code = str(uuid.uuid4())

            if not self.dry_run:
                target_cur.execute(
                    """
                    INSERT INTO wallets (
                      id, user_id, account_type, balance, balance_currency,
                      is_active, failed_withdraw_attempts, code, created_at, updated_at
                    ) VALUES (
                      %s, %s, 'teacher', 0.00, 'KES',
                      True, 0, %s, NOW(), NOW()
                    )
                    ON CONFLICT (user_id) DO NOTHING
                    RETURNING id;
                    """,
                    (wallet_id, user_id, wallet_code),
                )
                res = target_cur.fetchone()
                if res:
                    self.stats.increment(table, "inserted")
                else:
                    self.stats.increment(table, "skipped")
            else:
                self.stats.increment(table, "inserted")

    # ---------------------------------------------------------
    # Step 7: Teacher Profiles
    # ---------------------------------------------------------
    def migrate_teacher_profiles(self, legacy_cur, target_cur):
        table = "teacher_profiles"
        self.stats.init_table(table)
        logger.info("Step 7/13: Migrating teacher profiles with rate decomposition and KYC defaults...")

        legacy_cur.execute("SELECT * FROM teacher_profiles;")
        legacy_rows = legacy_cur.fetchall()

        for row in legacy_rows:
            self.stats.increment(table, "extracted")
            profile_id = str(row["id"])
            user_id = str(row.get("user_id"))

            if user_id not in self.migrated_user_ids:
                self.quarantine(table, profile_id, f"Associated user_id {user_id} was not migrated", row)
                continue

            hourly_rate = row.get("hourly_rate") or 0.00
            phone = (row.get("phone") or "+254700000000").strip()
            profile_picture = (row.get("profile_picture") or "profiles/default-teacher.png").strip()

            # Sanitize school FK
            school_id = str(row.get("school_id")) if row.get("school_id") else None
            if school_id and school_id not in self.school_ids:
                logger.info(f"Teacher {profile_id} references non-existent school {school_id}. Nullifying FK.")
                school_id = None

            curriculums = row.get("curriculums_taught") or ["CBC", "8-4-4"]
            if isinstance(curriculums, list):
                curriculums_json = json.dumps(curriculums)
            else:
                curriculums_json = json.dumps(["CBC", "8-4-4"])

            qualification = (row.get("highest_qualification") or "Bachelor of Education").strip()

            if not self.dry_run:
                target_cur.execute(
                    """
                    INSERT INTO teacher_profiles (
                      id, user_id, hourly_rate, hourly_rate_currency, is_verified, verification_status,
                      phone, profile_picture, curriculums_taught, highest_qualification, school_id,
                      education_level_id, teacher_license_number, tsc_number, academic_certificate,
                      teacher_license_certificate, bio, experience, gender, birth_date,
                      national_identity_number, national_identity_card, cv, paystack_recipient_code,
                      google_access_token, google_refresh_token, google_token_expiry
                    ) VALUES (
                      %s, %s, %s, 'KES', True, 'approved',
                      %s, %s, %s::jsonb, %s, %s,
                      %s, %s, %s, %s,
                      %s, %s, %s, %s, %s,
                      %s, %s, %s, %s,
                      %s, %s, %s
                    )
                    ON CONFLICT (user_id) DO UPDATE SET
                      is_verified = True,
                      verification_status = 'approved',
                      hourly_rate_currency = 'KES',
                      phone = EXCLUDED.phone,
                      profile_picture = EXCLUDED.profile_picture
                    RETURNING id;
                    """,
                    (
                        profile_id,
                        user_id,
                        hourly_rate,
                        phone,
                        profile_picture,
                        curriculums_json,
                        qualification,
                        school_id,
                        self.education_level_map.get("k12"),
                        row.get("teacher_license_number"),
                        row.get("tsc_number"),
                        row.get("academic_certificate"),
                        row.get("teacher_license_certificate"),
                        row.get("bio"),
                        row.get("experience") or 0,
                        row.get("gender"),
                        row.get("birth_date"),
                        row.get("national_identity_number"),
                        row.get("national_identity_card"),
                        row.get("cv"),
                        row.get("paystack_recipient_code"),
                        row.get("google_access_token"),
                        row.get("google_refresh_token"),
                        row.get("google_token_expiry"),
                    ),
                )
                self.migrated_teacher_ids.add(profile_id)
                self.stats.increment(table, "inserted")
            else:
                self.migrated_teacher_ids.add(profile_id)
                self.stats.increment(table, "inserted")

    # ---------------------------------------------------------
    # Step 8: Teacher Profiles Grade (M2M)
    # ---------------------------------------------------------
    def migrate_teacher_grades(self, legacy_cur, target_cur):
        table = "teacher_profiles_grade"
        self.stats.init_table(table)
        logger.info("Step 8/13: Migrating teacher grade associations (M2M)...")

        legacy_cur.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_name IN ('teacher_profiles_grade', 'users_teacherprofile_grade');
            """
        )
        found = legacy_cur.fetchone()
        if not found:
            logger.info("No legacy teacher_profiles_grade table found. Skipping.")
            return

        m2m_table = found["table_name"]
        legacy_cur.execute(f"SELECT * FROM {m2m_table};")
        legacy_rows = legacy_cur.fetchall()

        seen_pairs: Set[Tuple[str, str]] = set()

        for row in legacy_rows:
            self.stats.increment(table, "extracted")
            tp_id = str(row.get("teacherprofile_id") or row.get("teacher_profile_id"))
            gr_id = str(row.get("grade_id"))

            if tp_id not in self.migrated_teacher_ids:
                continue

            pair = (tp_id, gr_id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            if not self.dry_run:
                target_cur.execute(
                    """
                    INSERT INTO teacher_profiles_grade (teacherprofile_id, grade_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (tp_id, gr_id),
                )
                self.stats.increment(table, "inserted")
            else:
                self.stats.increment(table, "inserted")

    # ---------------------------------------------------------
    # Step 9: Teacher Profiles Subjects (M2M)
    # ---------------------------------------------------------
    def migrate_teacher_subjects(self, legacy_cur, target_cur):
        table = "teacher_profiles_subjects"
        self.stats.init_table(table)
        logger.info("Step 9/13: Migrating teacher subject associations (M2M)...")

        legacy_cur.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_name IN ('teacher_profiles_subjects', 'users_teacherprofile_subjects');
            """
        )
        found = legacy_cur.fetchone()
        if not found:
            logger.info("No legacy teacher_profiles_subjects table found. Skipping.")
            return

        m2m_table = found["table_name"]
        legacy_cur.execute(f"SELECT * FROM {m2m_table};")
        legacy_rows = legacy_cur.fetchall()

        seen_pairs: Set[Tuple[str, str]] = set()

        for row in legacy_rows:
            self.stats.increment(table, "extracted")
            tp_id = str(row.get("teacherprofile_id") or row.get("teacher_profile_id"))
            sub_id = str(row.get("subject_id"))

            if tp_id not in self.migrated_teacher_ids:
                continue

            pair = (tp_id, sub_id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            if not self.dry_run:
                target_cur.execute(
                    """
                    INSERT INTO teacher_profiles_subjects (teacherprofile_id, subject_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (tp_id, sub_id),
                )
                self.stats.increment(table, "inserted")
            else:
                self.stats.increment(table, "inserted")

    # ---------------------------------------------------------
    # Step 10: Courses
    # ---------------------------------------------------------
    def migrate_courses(self, legacy_cur, target_cur):
        table = "courses"
        self.stats.init_table(table)
        logger.info("Step 10/13: Migrating courses and curriculum root nodes...")

        legacy_cur.execute("SELECT * FROM courses;")
        legacy_rows = legacy_cur.fetchall()

        for row in legacy_rows:
            self.stats.increment(table, "extracted")
            course_id = str(row["id"])
            title = (row.get("title") or "").strip()
            if not title:
                self.quarantine(table, course_id, "Course title is empty", row)
                continue

            subject_id = str(row.get("subject_id")) if row.get("subject_id") else None
            teacher_id = str(row.get("teacher_id")) if row.get("teacher_id") else None
            grade_id = str(row.get("grade_id")) if row.get("grade_id") else None

            # Verify teacher FK
            if teacher_id and teacher_id not in self.migrated_teacher_ids:
                logger.info(f"Course {course_id} references un-migrated teacher {teacher_id}. Setting teacher_id to NULL.")
                teacher_id = None

            # Verify subject FK (non-nullable in Course model)
            if not subject_id:
                # Fallback to General Studies
                subject_id = self.subject_map.get("general studies") or next(iter(self.subject_map.values()), None)

            price = row.get("price") or 0.00
            ed_level_id = self.education_level_map.get("k12")

            if not self.dry_run:
                target_cur.execute(
                    """
                    INSERT INTO courses (
                      id, title, description, price, price_currency, is_active, is_universal, country,
                      cover_image, teacher_id, subject_id, grade_id, education_level_id, created_at, updated_at
                    ) VALUES (
                      %s, %s, %s, %s, 'KES', True, False, 'Kenya',
                      %s, %s, %s, %s, %s, COALESCE(%s, NOW()), NOW()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                      title = EXCLUDED.title,
                      price = EXCLUDED.price,
                      price_currency = EXCLUDED.price_currency,
                      country = EXCLUDED.country,
                      updated_at = NOW();
                    """,
                    (
                        course_id,
                        title,
                        row.get("description"),
                        price,
                        row.get("cover_image"),
                        teacher_id,
                        subject_id,
                        grade_id,
                        ed_level_id,
                        row.get("created_at"),
                    ),
                )
                self.migrated_course_ids.add(course_id)
                self.stats.increment(table, "inserted")
            else:
                self.migrated_course_ids.add(course_id)
                self.stats.increment(table, "inserted")

    # ---------------------------------------------------------
    # Step 11: Topics
    # ---------------------------------------------------------
    def migrate_topics(self, legacy_cur, target_cur):
        table = "topics"
        self.stats.init_table(table)
        logger.info("Step 11/13: Migrating course topics...")

        legacy_cur.execute("SELECT * FROM topics;")
        legacy_rows = legacy_cur.fetchall()

        for row in legacy_rows:
            self.stats.increment(table, "extracted")
            topic_id = str(row["id"])
            course_id = str(row.get("course_id"))

            if course_id not in self.migrated_course_ids:
                self.quarantine(table, topic_id, f"Topic references non-migrated course {course_id}", row)
                continue

            title = (row.get("title") or "").strip()
            if not title:
                self.quarantine(table, topic_id, "Topic title is empty", row)
                continue

            order = row.get("order") or 0
            is_locked = row.get("is_locked", True)

            if not self.dry_run:
                target_cur.execute(
                    """
                    INSERT INTO topics (
                      id, title, is_locked, "order", description, content_file, course_id, created_at, updated_at
                    ) VALUES (
                      %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()), NOW()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                      title = EXCLUDED.title,
                      updated_at = NOW();
                    """,
                    (
                        topic_id,
                        title,
                        is_locked,
                        order,
                        row.get("description"),
                        row.get("content_file"),
                        course_id,
                        row.get("created_at"),
                    ),
                )
                self.migrated_topic_ids.add(topic_id)
                self.stats.increment(table, "inserted")
            else:
                self.migrated_topic_ids.add(topic_id)
                self.stats.increment(table, "inserted")

    # ---------------------------------------------------------
    # Step 12: Subtopics
    # ---------------------------------------------------------
    def migrate_subtopics(self, legacy_cur, target_cur):
        table = "subtopics"
        self.stats.init_table(table)
        logger.info("Step 12/13: Migrating subtopics with empty content guard...")

        legacy_cur.execute("SELECT * FROM subtopics;")
        legacy_rows = legacy_cur.fetchall()

        for row in legacy_rows:
            self.stats.increment(table, "extracted")
            subtopic_id = str(row["id"])
            topic_id = str(row.get("topic_id"))

            if topic_id not in self.migrated_topic_ids:
                self.quarantine(table, subtopic_id, f"Subtopic references non-migrated topic {topic_id}", row)
                continue

            title = (row.get("title") or "").strip()
            if not title:
                self.quarantine(table, subtopic_id, "Subtopic title is empty", row)
                continue

            content = row.get("content")
            content_file = row.get("content_file")

            # DRF SubtopicSerializer.validate() guard: must have either content or content_file
            if not content and not content_file:
                content = "Lesson content to be updated."

            order = row.get("order") or 0
            is_locked = row.get("is_locked", True)

            if not self.dry_run:
                target_cur.execute(
                    """
                    INSERT INTO subtopics (
                      id, title, is_locked, "order", content, content_file, topic_id, created_at, updated_at
                    ) VALUES (
                      %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()), NOW()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                      title = EXCLUDED.title,
                      content = EXCLUDED.content,
                      updated_at = NOW();
                    """,
                    (
                        subtopic_id,
                        title,
                        is_locked,
                        order,
                        content,
                        content_file,
                        topic_id,
                        row.get("created_at"),
                    ),
                )
                self.stats.increment(table, "inserted")
            else:
                self.stats.increment(table, "inserted")

    # ---------------------------------------------------------
    # Step 13: Revision Materials
    # ---------------------------------------------------------
    def migrate_revision_materials(self, legacy_cur, target_cur):
        table = "revision_materials"
        self.stats.init_table(table)
        logger.info("Step 13/13: Migrating revision materials (mapping file_url -> file)...")

        legacy_cur.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_name = 'revision_materials';
            """
        )
        if not legacy_cur.fetchone():
            logger.info("No revision_materials table in legacy database. Skipping.")
            return

        legacy_cur.execute("SELECT * FROM revision_materials;")
        legacy_rows = legacy_cur.fetchall()

        for row in legacy_rows:
            self.stats.increment(table, "extracted")
            mat_id = str(row["id"])
            title = (row.get("title") or "").strip()
            if not title:
                self.quarantine(table, mat_id, "Revision material title is empty", row)
                continue

            # Migration 0006 refactored file_url -> file
            file_path = row.get("file") or row.get("file_url")

            course_id = str(row.get("course_id")) if row.get("course_id") else None
            if course_id and course_id not in self.migrated_course_ids:
                course_id = None

            uploaded_by_id = str(row.get("uploaded_by_id")) if row.get("uploaded_by_id") else None
            if uploaded_by_id and uploaded_by_id not in self.migrated_teacher_ids:
                uploaded_by_id = None

            if not self.dry_run:
                target_cur.execute(
                    """
                    INSERT INTO revision_materials (
                      id, title, description, file, course_id, uploaded_by_id, created_at, updated_at
                    ) VALUES (
                      %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()), NOW()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                      title = EXCLUDED.title,
                      file = EXCLUDED.file,
                      updated_at = NOW();
                    """,
                    (
                        mat_id,
                        title,
                        row.get("description"),
                        file_path,
                        course_id,
                        uploaded_by_id,
                        row.get("created_at"),
                    ),
                )
                self.stats.increment(table, "inserted")
            else:
                self.stats.increment(table, "inserted")

    # ---------------------------------------------------------
    # Main Pipeline Runner
    # ---------------------------------------------------------
    def run(self):
        logger.info("Starting StudyBuddy Africa Legacy Data Migration Pipeline...")
        logger.info(f"Execution Mode: {'DRY-RUN (Tier 0 Read-Only)' if self.dry_run else 'LIVE IMPORT (Tier 1 Code & Commit)'}")

        legacy_conn = self.connect_db(self.legacy_url, read_only=True)
        target_conn = self.connect_db(self.target_url, read_only=False)

        try:
            with legacy_conn.cursor(cursor_factory=RealDictCursor) as legacy_cur, target_conn.cursor(
                cursor_factory=RealDictCursor
            ) as target_cur:

                self.load_target_caches(target_cur)

                # DAG Execution
                self.migrate_education_levels(target_cur)
                self.migrate_grades(legacy_cur, target_cur)
                self.migrate_subjects(legacy_cur, target_cur)
                self.migrate_schools(legacy_cur, target_cur)
                self.migrate_users(legacy_cur, target_cur)
                self.migrate_wallets(target_cur)
                self.migrate_teacher_profiles(legacy_cur, target_cur)
                self.migrate_teacher_grades(legacy_cur, target_cur)
                self.migrate_teacher_subjects(legacy_cur, target_cur)
                self.migrate_courses(legacy_cur, target_cur)
                self.migrate_topics(legacy_cur, target_cur)
                self.migrate_subtopics(legacy_cur, target_cur)
                self.migrate_revision_materials(legacy_cur, target_cur)

                if not self.dry_run:
                    target_conn.commit()
                    logger.info("Transaction committed successfully to PostgreSQL 17 target database.")
                else:
                    target_conn.rollback()
                    logger.info("Dry-run complete. All target changes rolled back.")

        except Exception as e:
            target_conn.rollback()
            logger.error(f"Migration pipeline encountered fatal error: {e}", exc_info=True)
            raise
        finally:
            legacy_conn.close()
            target_conn.close()
            self.save_quarantine_report()
            self.stats.print_summary()


def parse_args():
    parser = argparse.ArgumentParser(
        description="StudyBuddy Africa Legacy Supabase Migration ETL Script (Phase 2)"
    )
    parser.add_argument(
        "--legacy-url",
        default=os.getenv("LEGACY_DATABASE_URL"),
        help="PostgreSQL connection URL for legacy Supabase database (or env LEGACY_DATABASE_URL)",
    )
    parser.add_argument(
        "--target-url",
        default=os.getenv("TARGET_DATABASE_URL"),
        help="PostgreSQL connection URL for active PG17 database (or env TARGET_DATABASE_URL)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate extraction, transformation and resolution without writing to target",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for querying/inserting (default 100)",
    )
    parser.add_argument(
        "--quarantine-file",
        default=None,
        help="Path for quarantined failure records JSON",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if not args.legacy_url or not args.target_url:
        logger.error(
            "Both --legacy-url and --target-url (or LEGACY_DATABASE_URL and TARGET_DATABASE_URL) are required.\n"
            "Example: python scripts/migrate_legacy_supabase_data.py --legacy-url \"postgresql://...\" --target-url \"postgresql://...\" --dry-run"
        )
        sys.exit(1)

    migrator = LegacyDataMigrator(
        legacy_url=args.legacy_url,
        target_url=args.target_url,
        dry_run=args.dry_run,
        batch_size=args.batch_size,
        quarantine_file=args.quarantine_file,
    )
    migrator.run()
