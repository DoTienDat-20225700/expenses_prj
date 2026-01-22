#!/usr/bin/env python
"""
Debug script to check Cloudinary configuration on production
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings

print("=" * 60)
print("CLOUDINARY DEBUG INFO")
print("=" * 60)
print(f"DEBUG: {settings.DEBUG}")
print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
print("-" * 60)
print(f"DEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', 'NOT SET - using default')}")
print("-" * 60)

# Check env vars
cloudinary_name = os.getenv('CLOUDINARY_CLOUD_NAME', 'NOT SET')
cloudinary_key = os.getenv('CLOUDINARY_API_KEY', 'NOT SET')
cloudinary_secret = os.getenv('CLOUDINARY_API_SECRET', 'NOT SET')

print(f"CLOUDINARY_CLOUD_NAME env: {cloudinary_name[:10]}... (hidden)" if cloudinary_name != 'NOT SET' else f"CLOUDINARY_CLOUD_NAME env: {cloudinary_name}")
print(f"CLOUDINARY_API_KEY env: {cloudinary_key[:5]}... (hidden)" if cloudinary_key != 'NOT SET' else f"CLOUDINARY_API_KEY env: {cloudinary_key}")
print(f"CLOUDINARY_API_SECRET env: {'SET' if cloudinary_secret != 'NOT SET' else 'NOT SET'}")
print("-" * 60)

# Try to import cloudinary
try:
    import cloudinary
    print(f"✅ Cloudinary imported successfully")
    print(f"Cloudinary config: {cloudinary.config().cloud_name}")
except Exception as e:
    print(f"❌ Error importing cloudinary: {e}")

print("=" * 60)
