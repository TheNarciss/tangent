"""enablebanking: accounts keyed by identification_hash, one consent per bank

An account's uid is scoped to the Enable Banking session, so two consents
for the same bank stored every account twice, with its transactions. The
identification_hash is the identity that survives a consent. This
migration keeps, per user and bank, the newest consent and the accounts it
read, drops the duplicates, and re-keys what remains on the hash.

Revision ID: c9e1a4b6d8f0
Revises: b8d0f3a5c7e9
Create Date: 2026-09-14
"""

from alembic import op

revision = "c9e1a4b6d8f0"
down_revision = "b8d0f3a5c7e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Accounts read by an older consent, when the newest consent read the
    #    same account (same hash): gone, with their transactions (FK cascade).
    op.execute(
        """
        WITH newest AS (
            SELECT DISTINCT ON (user_id, bank_name) id, user_id
            FROM enablebanking_sessions
            ORDER BY user_id, bank_name, created_at DESC
        )
        DELETE FROM bank_accounts a
        USING bank_accounts b, newest n
        WHERE a.provider = 'enablebanking'
          AND b.provider = 'enablebanking'
          AND a.user_id = b.user_id
          AND a.user_id = n.user_id
          AND a.id <> b.id
          AND a.raw_data->>'identification_hash' IS NOT NULL
          AND a.raw_data->>'identification_hash' = b.raw_data->>'identification_hash'
          AND b.raw_data->>'enablebanking_session' = n.id::text
          AND a.raw_data->>'enablebanking_session' <> n.id::text
        """
    )
    # 2. Older consents for the same bank: gone. (Their access at the bank
    #    lapses with valid_until; the user can also revoke it in the bank's app.)
    op.execute(
        """
        WITH newest AS (
            SELECT DISTINCT ON (user_id, bank_name) id, user_id, bank_name
            FROM enablebanking_sessions
            ORDER BY user_id, bank_name, created_at DESC
        )
        DELETE FROM enablebanking_sessions s
        USING newest n
        WHERE s.user_id = n.user_id AND s.bank_name = n.bank_name AND s.id <> n.id
        """
    )
    # 3. Orphans of a deleted consent: gone too.
    op.execute(
        """
        DELETE FROM bank_accounts a
        WHERE a.provider = 'enablebanking'
          AND NOT EXISTS (
              SELECT 1 FROM enablebanking_sessions s
              WHERE s.id::text = a.raw_data->>'enablebanking_session'
          )
        """
    )
    # 4. What remains is keyed on the stable identity, when it is unique for
    #    the user (two pockets sharing a hash keep their uid).
    op.execute(
        """
        UPDATE bank_accounts a
        SET provider_account_id = left(a.raw_data->>'identification_hash', 64)
        WHERE a.provider = 'enablebanking'
          AND a.raw_data->>'identification_hash' IS NOT NULL
          AND (
              SELECT count(*) FROM bank_accounts b
              WHERE b.user_id = a.user_id AND b.provider = 'enablebanking'
                AND b.raw_data->>'identification_hash' = a.raw_data->>'identification_hash'
          ) = 1
        """
    )


def downgrade() -> None:
    # The uid of the day is still in raw_data; nothing else can be restored.
    op.execute(
        """
        UPDATE bank_accounts
        SET provider_account_id = raw_data->>'uid'
        WHERE provider = 'enablebanking' AND raw_data->>'uid' IS NOT NULL
        """
    )
