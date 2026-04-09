# generate_hash.py
from werkzeug.security import generate_password_hash

# Change this to your actual password
PASSWORD = "Admin1!"

# Generate the hash
new_hash = generate_password_hash(PASSWORD)

print("=" * 50)
print("NEW PASSWORD HASH GENERATED")
print("=" * 50)
print(f"Password: {PASSWORD}")
print(f"\nHash: {new_hash}")
print("=" * 50)
print("\nCopy this hash and use it in MySQL:")
print(f"UPDATE admin SET password = '{new_hash}' WHERE username = 'admin';")