"""Initialize the database: create indexes, seed user_profile if missing.

Run once after deploying schema changes:
    PYTHONPATH=. uv run python scripts/init_db.py
"""

from app.config.settings import settings
from app.db.client import Collections, ping
from app.db.indexes import ensure_all_indexes
from app.models.user_profile import UserProfile


def seed_user_profile() -> None:
    """Insert your user_profile if it doesn't exist yet."""
    coll = Collections.user_profile()
    existing = coll.find_one({"_id": "sahil"})
    if existing:
        print(
            f"  user_profile 'sahil' already exists (created {existing.get('created_at')})"
        )
        return

    profile = UserProfile(
        display_name=settings.RESEND_TO.split("@")[0].title().replace(".", " "),
        email=settings.RESEND_TO,
        # Everything else uses sensible defaults; you can edit via API or directly later
    )
    coll.insert_one(profile.to_mongo())
    print(f"  ✓ Seeded user_profile 'sahil' ({profile.email})")


def main() -> None:
    print("Database initialization")
    print("─" * 60)
    print(f"  URI:    {settings.MONGODB_URI.split('@')[1].split('/')[0]}")
    print(f"  DB:     {settings.MONGODB_DB_NAME}")
    print()

    print("Pinging Atlas...")
    if not ping():
        print("  ✗ Atlas is unreachable. Check IP allowlist + connection string.")
        raise SystemExit(1)
    print("  ✓ Atlas reachable")
    print()

    print("Ensuring indexes...")
    results = ensure_all_indexes()
    for collection_name, index_names in results.items():
        print(f"  ✓ {collection_name:20s} -> {len(index_names)} indexes")
    print()

    print("Seeding user_profile...")
    seed_user_profile()
    print()

    print("✅ DB initialization complete")


if __name__ == "__main__":
    main()
