"""
Seed initial data: groups and test users
Run with: python manage.py shell < seed_data.py
"""
from django.contrib.auth.models import User
from transfer_app.models import UserProfile, Group

# Create groups
groups_data = [
    ('Production Line 1', 'PL1'),
    ('Production Line 2', 'PL2'),
    ('Quality Control', 'QC'),
    ('Assembly', 'ASM'),
    ('Packaging', 'PKG'),
]

print("Creating groups...")
for name, code in groups_data:
    group, created = Group.objects.get_or_create(code=code, defaults={'name': name})
    if created:
        print(f"  ✓ Created: {group}")
    else:
        print(f"  - Exists: {group}")

# Create test users
users_data = [
    ('supervisor1', 'pass123', 'SUPERVISOR', 'SV001'),
    ('lead1', 'pass123', 'LEAD', 'LD001'),
    ('processor1', 'pass123', 'DATA_PROCESSOR', 'DP001'),
]

print("\nCreating test users...")
for username, password, role, msnv in users_data:
    if User.objects.filter(username=username).exists():
        print(f"  - User '{username}' already exists")
    else:
        user = User.objects.create_user(username=username, password=password)
        UserProfile.objects.create(user=user, role=role, msnv=msnv)
        print(f"  ✓ Created: {username} ({role}) - password: {password}")

print("\n✅ Seed data complete!")
print("\nTest accounts:")
print("  supervisor1 / pass123 (can create requests)")
print("  lead1 / pass123 (can approve)")
print("  processor1 / pass123 (can confirm)")
