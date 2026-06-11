"""i18n/l10n foundation — content translations + diner locale + tenant currency

Three INDEPENDENT axes (Grab-validated): language=person (customers.locale + menu translations),
currency=settlement (merchants.currency), timezone=place (already on the node, untouched here).

- menu_categories.translations / menu_items.translations: optional override/cache {locale:{name,description}}
  over the canonical name/description; NULL = canonical-only. Lays the slot BEFORE the menu is seeded so
  translations are never a retrofit/backfill.
- customers.locale: the diner's preferred UI language (NULL → resolve tenant default → Accept-Language → en).
- merchants.currency: ISO 4217 settlement currency (NOT NULL default SGD; money never crosses, FX deferred).

Revision ID: k5l6i18n
Revises: j4k5theme
Create Date: 2026-06-11
"""
import sqlalchemy as sa
from alembic import op

revision = "k5l6i18n"
down_revision = "j4k5theme"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("menu_categories", sa.Column("translations", sa.JSON(), nullable=True))
    op.add_column("menu_items", sa.Column("translations", sa.JSON(), nullable=True))
    op.add_column("customers", sa.Column("locale", sa.String(length=8), nullable=True))
    op.add_column(
        "merchants",
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="SGD"),
    )


def downgrade() -> None:
    op.drop_column("merchants", "currency")
    op.drop_column("customers", "locale")
    op.drop_column("menu_items", "translations")
    op.drop_column("menu_categories", "translations")
