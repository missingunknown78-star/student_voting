# add_access_code.py
import pymysql
from datetime import datetime, timedelta

connection = pymysql.connect(
    host='localhost',
    user='root',
    password='',  # Your MySQL password if any
    database='student_voting'
)

try:
    with connection.cursor() as cursor:
        # Delete any existing access codes (optional - for fresh start)
        cursor.execute("DELETE FROM access_codes")
        
        # Insert new access code
        sql = """INSERT INTO access_codes (code, secret_path, description, is_active, created_at, expires_at) 
                 VALUES (%s, %s, %s, %s, %s, %s)"""
        
        cursor.execute(sql, (
            '1234567',
            'access',
            'Default access code for exhibit',
            1,  # is_active = True
            datetime.now(),
            datetime.now() + timedelta(days=30)
        ))
        
        connection.commit()
        
        print("=" * 50)
        print("✅ ACCESS CODE CREATED SUCCESSFULLY!")
        print("=" * 50)
        print(f"Code: 1234567")
        print(f"Secret Path: access")
        print(f"Description: Default access code for exhibit")
        print(f"Active: Yes")
        print(f"Expires: {(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        print("\n🔐 Admin access URL:")
        print("   http://localhost:5000/admin/access")
        
finally:
    connection.close()