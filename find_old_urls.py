import os
import re

def scan_files_for_old_urls(directory='.'):
    """Scan all files for hardcoded /student URLs"""
    
    # Patterns to search for
    patterns = [
        r'fetch\([\'"]/student/',           # fetch('/student/
        r'fetch\([\'"]\/student/',           # fetch("/student/
        r'url: [\'"]/student/',              # url: '/student/
        r'url: [\'"]\/student/',             # url: "/student/
        r'window\.location\.href = [\'"]/student/',  # window.location.href = '/student/
        r'action=[\'"]/student/',             # action='/student/
        r'action=[\'"]\/student/',            # action="/student/
        r'href=[\'"]/student/',               # href='/student/
        r'href=[\'"]\/student/',              # href="/student/
        r'"/student/',                         # "/student/
        r"'/student/",                         # '/student/
    ]
    
    file_extensions = ['.html', '.js', '.py', '.css']
    
    print("=" * 60)
    print("🔍 SCANNING FOR OLD /student URLS...")
    print("=" * 60)
    
    found_files = []
    
    for root, dirs, files in os.walk(directory):
        # Skip virtual environment and hidden directories
        if 'venv' in root or '.git' in root or '__pycache__' in root:
            continue
            
        for file in files:
            if any(file.endswith(ext) for ext in file_extensions):
                filepath = os.path.join(root, file)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        for pattern in patterns:
                            matches = re.findall(pattern, content)
                            if matches:
                                print(f"\n📁 {filepath}")
                                print(f"   Found {len(matches)} old URL(s)")
                                
                                # Show context lines
                                lines = content.split('\n')
                                for i, line in enumerate(lines, 1):
                                    if re.search(pattern, line):
                                        print(f"   Line {i}: {line.strip()}")
                                
                                if filepath not in found_files:
                                    found_files.append(filepath)
                                break
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    print("\n" + "=" * 60)
    print(f"✅ Scan complete! Found old URLs in {len(found_files)} file(s)")
    
    if found_files:
        print("\n📋 Files to fix:")
        for f in found_files:
            print(f"   - {f}")
    
    return found_files

def suggest_fixes():
    """Suggest the correct url_for replacements"""
    print("\n" + "=" * 60)
    print("🔧 SUGGESTED FIXES")
    print("=" * 60)
    
    fixes = [
        ("fetch('/student/webauthn/register/options'", 
         "fetch(\"{{ url_for('student.webauthn_register_options') }}\""),
        
        ("fetch('/student/webauthn/register/verify'", 
         "fetch(\"{{ url_for('student.webauthn_register_verify') }}\""),
        
        ("fetch('/student/webauthn/login/options'", 
         "fetch(\"{{ url_for('student.webauthn_login_options') }}\""),
        
        ("fetch('/student/webauthn/login/verify'", 
         "fetch(\"{{ url_for('student.webauthn_login_verify') }}\""),
        
        ("fetch('/student/verify-device/status'", 
         "fetch(\"{{ url_for('student.verify_device_status') }}\""),
        
        ("fetch('/student/verify-device/resend'", 
         "fetch(\"{{ url_for('student.resend_verify_device') }}\""),
        
        ("action='/student/", 
         "action=\"{{ url_for('student.", ".', _external=False) }}\""),
        
        ("href='/student/", 
         "href=\"{{ url_for('student.", ".', _external=False) }}\""),
    ]
    
    print("\nReplace these patterns:")
    for old, new in fixes:
        print(f"\n❌ {old}...")
        print(f"✅ {new}...")

if __name__ == "__main__":
    # Scan current directory
    found = scan_files_for_old_urls('.')
    
    if found:
        suggest_fixes()
    else:
        print("\n🎉 No old /student URLs found! Good job!")