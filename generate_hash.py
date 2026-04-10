# generate_bcrypt_hash.py
from flask_bcrypt import Bcrypt
import sys

# Initialize bcrypt
bcrypt = Bcrypt()

# Your password
password = "Admin1!"

# Generate hash (exactly like your admin creation script)
hashed = bcrypt.generate_password_hash(password).decode('utf-8')

print("=" * 60)
print("BCRYPT HASH GENERATED (Compatible with your app)")
print("=" * 60)
print(f"Password: {password}")
print(f"\nHash: {hashed}")
print(f"\nHash length: {len(hashed)} characters")
print(f"Starts with $2b$? {hashed.startswith('$2b$')}")
print("=" * 60)
print("\nRun this SQL command:")
print(f"UPDATE admins SET password = '{hashed}' WHERE username = 'admin';")