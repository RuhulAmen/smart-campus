"""
Quick diagnostic script to verify MongoDB Atlas credentials and connectivity.
Usage:
    python backend/test_atlas.py
"""
import os
import sys

try:
    import certifi
    from pymongo import MongoClient
    from dotenv import load_dotenv
except ImportError:
    print("Installing requirements: pymongo certifi python-dotenv dnspython...")
    os.system(f"{sys.executable} -m pip install pymongo certifi python-dotenv dnspython")
    import certifi
    from pymongo import MongoClient
    from dotenv import load_dotenv

# Load .env
root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
if os.path.exists(root_env):
    load_dotenv(root_env)

default_uri = os.getenv('MONGO_URI', '')

print("=" * 60)
print("🔍 MongoDB Atlas Connection Diagnostic Tool")
print("=" * 60)

user_input = input(f"Enter MONGO_URI to test (or press Enter to use .env):\n> ").strip()
uri = user_input if user_input else default_uri

if not uri:
    print("❌ No MONGO_URI provided or found in .env!")
    sys.exit(1)

# Mask password for display
if '@' in uri and '://' in uri:
    prefix = uri.split('://')[0] + '://'
    user_pass = uri.split('://')[1].split('@')[0]
    host_part = uri.split('@')[1]
    username = user_pass.split(':')[0]
    masked = f"{prefix}{username}:****@{host_part}"
else:
    masked = uri

print(f"\nTesting connection to: {masked}")

# Ensure authSource=admin for SRV connections if omitted
if uri.startswith('mongodb+srv://') and 'authSource=' not in uri:
    sep = '&' if '?' in uri else '?'
    uri = f"{uri}{sep}authSource=admin"
    print(f"ℹ️ Automatically appended authSource=admin")

try:
    client = MongoClient(
        uri,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=10000,
        connect=True
    )
    client.admin.command('ping')
    print("\n✅ SUCCESS! Authenticated and connected to MongoDB Atlas successfully!")
    dbs = client.list_database_names()
    print(f"📦 Databases found on cluster: {dbs}")
except Exception as e:
    print(f"\n❌ Connection FAILED: {e}")
    print("\nTroubleshooting tips:")
    print("1. Go to cloud.mongodb.com -> Security -> Database Access")
    print("2. Verify the username matches exactly and click 'Edit' -> 'Edit Password'")
    print("3. Avoid '@' or special characters in the password to prevent URL encoding errors")
    print("4. Update your .env and Vercel environment variables with the new URI")

