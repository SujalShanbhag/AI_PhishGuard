import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models.database_models import User
from app.security.authentication import hash_password

def initialize_database():
    print(f"[VERITAS AI] Initializing database at: {settings.DATABASE_URL}")
    settings.ensure_directories()
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if default analyst users exist
        for email, pwd, name in [
            ("analyst@phishguard.ai", "PhishGuardAdmin2026!", "PhishGuard Lead Analyst"),
            ("analyst@veritas.ai", "VeritasAdmin2026!", "Forensic Analyst")
        ]:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                print(f"[AI PhishGuard] Creating default account: {email}")
                user = User(
                    email=email,
                    password_hash=hash_password(pwd),
                    full_name=name,
                    role="lead_analyst"
                )
                db.add(user)
                db.commit()
                print(f"[AI PhishGuard] Account created: {email} / {pwd}")
            else:
                print(f"[AI PhishGuard] Account {email} already exists.")
    finally:
        db.close()
    print("[VERITAS AI] Database schema initialized successfully.")

if __name__ == "__main__":
    initialize_database()
