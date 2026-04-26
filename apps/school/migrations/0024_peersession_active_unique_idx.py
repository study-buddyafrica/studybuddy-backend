"""
Partial unique index: only one active PeerSession per (initiator, peer, course).
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("school", "0023_escrow_wallet_and_paystack"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE UNIQUE INDEX IF NOT EXISTS
                peer_sessions_active_unique
            ON peer_sessions (initiator_id, peer_id, course_id)
            WHERE status = 'active';
            """,
            reverse_sql="DROP INDEX IF EXISTS peer_sessions_active_unique;",
        ),
    ]
