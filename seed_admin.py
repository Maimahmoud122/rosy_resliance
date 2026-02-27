"""
seed_admin.py
─────────────
Run this ONCE to create the first admin account.

Usage:
    python seed_admin.py

This script will:
    1. Connect to the database
    2. Check if admin already exists
    3. Create a User (role=admin) + Admin profile
    4. Print the credentials to the terminal
"""

from app import create_app, db, bcrypt
from models import User, UserRole
from models.admin import Admin
import uuid

# ── Admin credentials — change these before running ──────
ADMIN_EMAIL     = "admin@hospital.com"
ADMIN_PASSWORD  = "Admin@123456"       # change this!
ADMIN_FULL_NAME = "System Admin"
SALT_ROUNDS     = 12


def seed_admin():
    app = create_app()

    with app.app_context():

        # 1. Check if admin already exists
        existing = User.query.filter_by(email=ADMIN_EMAIL).first()
        if existing:
            print(f"\n⚠️  Admin already exists with email: {ADMIN_EMAIL}")
            print("If you need to reset the password, delete the account and run again.\n")
            return

        try:
            # 2. Hash password
            password_hash = bcrypt.generate_password_hash(
                ADMIN_PASSWORD, rounds=SALT_ROUNDS
            ).decode("utf-8")

            # 3. Create User
            admin_user = User(
                email          = ADMIN_EMAIL,
                password_hash  = password_hash,
                role           = UserRole.admin,
                full_name      = ADMIN_FULL_NAME,
                is_active      = True,
                email_verified = True,   # admin is pre-verified
            )
            db.session.add(admin_user)
            db.session.flush()

            # 4. Create Admin profile
            admin_profile = Admin(
                admin_id = admin_user.user_id,
            )
            db.session.add(admin_profile)
            db.session.commit()

            print("\n" + "═" * 45)
            print("✅  Admin account created successfully!")
            print("═" * 45)
            print(f"  Email    : {ADMIN_EMAIL}")
            print(f"  Password : {ADMIN_PASSWORD}")
            print(f"  User ID  : {admin_user.user_id}")
            print("═" * 45)
            print("⚠️  Change the password after first login!\n")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Failed to create admin: {e}\n")


if __name__ == "__main__":
    seed_admin()