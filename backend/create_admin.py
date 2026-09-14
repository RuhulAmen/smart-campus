"""
Create the first admin account for Smart Campus.

New self-service signups always get the 'student' role (see routes/auth.py),
so an admin account has to be provisioned explicitly with this script.

Usage (run from the backend/ directory):

    python create_admin.py --email admin@campus.edu --password 'a-strong-password'

Alternatively set ADMIN_EMAIL / ADMIN_PASSWORD in your .env and run:

    python create_admin.py
"""

import argparse
import getpass
import os
import re
import sys

import bcrypt
from dotenv import load_dotenv
from pymongo import MongoClient

root_env = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))
backend_env = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
if os.path.exists(root_env):
    load_dotenv(root_env)
if os.path.exists(backend_env):
    load_dotenv(backend_env)

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/smart_campus')
DB_NAME = os.getenv('MONGO_DB_NAME', 'smart_campus')
MONGO_TIMEOUT_MS = int(os.getenv('MONGO_SERVER_SELECTION_TIMEOUT_MS', '5000'))

EMAIL_REGEX = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'


def main():
    parser = argparse.ArgumentParser(description='Provision an admin account for Smart Campus')
    parser.add_argument('--email', default=os.getenv('ADMIN_EMAIL'), help='Admin email address')
    parser.add_argument('--password', default=os.getenv('ADMIN_PASSWORD'), help='Admin password (or use the ADMIN_PASSWORD env var)')
    parser.add_argument('--full-name', default=os.getenv('ADMIN_FULL_NAME', 'Campus Administrator'), help='Admin full name')
    parser.add_argument('--student-id', default=os.getenv('ADMIN_STUDENT_ID', 'ADMIN-001'), help='Admin student/staff ID')
    args = parser.parse_args()

    email = (args.email or '').strip()
    if not email or not re.match(EMAIL_REGEX, email):
        sys.exit('A valid --email is required (or set ADMIN_EMAIL in .env)')

    password = args.password
    if not password:
        password = getpass.getpass('Admin password: ')
    if len(password) < 6:
        sys.exit('Password must be at least 6 characters long')

    print(f'Connecting to database "{DB_NAME}"...')
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=MONGO_TIMEOUT_MS)
        client.admin.command('ping')
    except Exception as e:
        sys.exit(f'❌ Could not connect to MongoDB ({e}).\n'
                 '   Please check your MONGO_URI, network connection, and MongoDB Atlas IP Access List.')

    collection = client[DB_NAME]['users']

    # Case-insensitive duplicate check
    existing = collection.find_one({
        'email': re.compile('^' + re.escape(email) + '$', re.IGNORECASE)
    })
    if existing:
        print(f'An account with email {email} already exists (role: {existing.get("role", "unknown")}).')
        if existing.get('role') == 'admin':
            print('It is already an admin — nothing to do.')
        else:
            print(f'Promoting it to admin? Run: python create_admin.py again is not needed — '
                  f'update the role in MongoDB manually instead.')
        client.close()
        sys.exit(1)

    from datetime import datetime
    admin = {
        'full_name': args.full_name.strip(),
        'email': email,
        'student_id': args.student_id.strip(),
        'password': bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()),
        'role': 'admin',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'is_active': True,
    }

    result = collection.insert_one(admin)
    client.close()

    print(f'✅ Admin account created with ID {result.inserted_id}')
    print(f'You can now log in at http://localhost:5000/login with {email}')


if __name__ == '__main__':
    main()
