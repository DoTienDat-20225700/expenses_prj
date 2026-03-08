#!/usr/bin/env python3
from decouple import config
import os

print('Current directory:', os.getcwd())
print('.env file exists:', os.path.exists('.env'))
print()
print('Reading EMAIL_HOST from decouple:')
email_host = config('EMAIL_HOST', default='NOT_FOUND')
print(f"  EMAIL_HOST: '{email_host}'")
print(f"  Length: {len(email_host)}")
print(f"  Repr: {repr(email_host)}")
print()
print('Direct .env content (EMAIL_HOST lines):')
with open('.env', 'r') as f:
    for i, line in enumerate(f, 1):
        if 'EMAIL_HOST' in line:
            print(f"  Line {i}: {repr(line.rstrip())}")
