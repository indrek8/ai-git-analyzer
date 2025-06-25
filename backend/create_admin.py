#!/usr/bin/env python3
"""
Create an admin user for the Git Analytics Platform
"""
import sys
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.database import SessionLocal, engine
from app.models import Base, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin_user():
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if admin user already exists
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if existing_admin:
            print("Admin user already exists!")
            print(f"Username: {existing_admin.username}")
            print(f"Email: {existing_admin.email}")
            print(f"Active: {existing_admin.is_active}")
            return
        
        # Create admin user
        hashed_password = pwd_context.hash("admin123")
        admin_user = User(
            username="admin",
            email="admin@gitanalytics.local",
            hashed_password=hashed_password,
            full_name="Administrator",
            is_active=True,
            is_admin=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ Admin user created successfully!")
        print("Username: admin")
        print("Password: admin123")
        print("Email: admin@gitanalytics.local")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()