#!/usr/bin/env python3
"""
Debug script to check environment variables in Railway
"""

import os

print("🔍 Environment Variables Debug")
print("=" * 50)

# Check all environment variables
all_vars = dict(os.environ)
print(f"📊 Total environment variables: {len(all_vars)}")

# Check for database-related variables
db_vars = {k: v for k, v in all_vars.items() if any(keyword in k.upper() for keyword in ['DATABASE', 'POSTGRES', 'PG', 'DB'])}
print(f"\n🗄️ Database-related variables ({len(db_vars)}):")
for key, value in db_vars.items():
    # Show first 50 chars of value for security
    display_value = value[:50] + "..." if len(value) > 50 else value
    print(f"  {key}: {display_value}")

# Check for Railway-specific variables
railway_vars = {k: v for k, v in all_vars.items() if 'RAILWAY' in k.upper()}
print(f"\n🚂 Railway variables ({len(railway_vars)}):")
for key, value in railway_vars.items():
    print(f"  {key}: {value}")

# Check for any variables that might contain database URLs
url_vars = {k: v for k, v in all_vars.items() if 'postgresql://' in v.lower() or 'postgres://' in v.lower()}
print(f"\n🔗 Variables containing PostgreSQL URLs ({len(url_vars)}):")
for key, value in url_vars.items():
    display_value = value[:50] + "..." if len(value) > 50 else value
    print(f"  {key}: {display_value}")

print("\n" + "=" * 50)
print("✅ Debug complete")
