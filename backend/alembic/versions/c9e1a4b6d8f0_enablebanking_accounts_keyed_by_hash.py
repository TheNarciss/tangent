"""enablebanking: accounts keyed by identification_hash, one consent per bank

An account's uid is scoped to the Enable Banking session, so two consents
for the same bank stored every account twice, with its transactions. The
identification_hash is the identity that survives a consent; its SHA-256
digest fits the 64-character key column without losing what distinguishes
two accounts (the first 80 characters of the hash are the same for every
account of a bank).

This migration keeps, per user and per hash, the account row that carries
the most transactions (the first read after a consent has the long
history), drops the others with their transactions, keeps the newest
consent per bank and re-tags the accounts to it, and re-keys on the digest.

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
    # 1. Accounts without a hash cannot be matched to anything: the next read
    #    recreates them under a stable key.
    op.execute(
        """
        DELETE FROM bank_accounts
        WHERE provider = 'enablebanking'
          AND (raw_data->>'identification_hash') IS NULL
        """
    )
    # 2. One row per (user, hash): the one with the most transactions, then
    #    the most recently read. The others go, with their transactions.
    op.execute(
        """
        WITH ranked AS (
            SELECT a.id,
                   row_number() OVER (
                       PARTITION BY a.user_id, a.raw_data->>'identification_hash'
                       ORDER BY (SELECT count(*) FROM bank_transactions t
                                 WHERE t.bank_account_id = a.id) DESC,
                                a.last_synced_at DESC NULLS LAST,
                                a.id
                   ) AS rank
            FROM bank_accounts a
            WHERE a.provider = 'enablebanking'
        )
        DELETE FROM bank_accounts
        WHERE id IN (SELECT id FROM ranked WHERE rank > 1)
        """
    )
    # 3. One consent per (user, bank): the newest. The surviving accounts of
    #    that bank are re-tagged to it, so that unlinking still takes them.
    op.execute(
        """
        WITH newest AS (
            SELECT DISTINCT ON (user_id, bank_name) id, user_id, bank_name
            FROM enablebanking_sessions
            ORDER BY user_id, bank_name, created_at DESC
        )
        UPDATE bank_accounts a
        SET raw_data = a.raw_data || jsonb_build_object('enablebanking_session', n.id::text)
        FROM newest n
        WHERE a.provider = 'enablebanking'
          AND a.user_id = n.user_id
          AND a.institution_name = n.bank_name
        """
    )
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
    # 4. The stable key: a digest of the hash.
    op.execute(
        """
        UPDATE bank_accounts
        SET provider_account_id = encode(
            sha256(convert_to(raw_data->>'identification_hash', 'UTF8')), 'hex'
        )
        WHERE provider = 'enablebanking'
          AND (raw_data->>'identification_hash') IS NOT NULL
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
