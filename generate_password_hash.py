#!/usr/bin/env python3
"""Utility script to generate bcrypt password hashes for config.yaml."""
import bcrypt
import sys

if len(sys.argv) < 2:
    print("Usage: python generate_password_hash.py <password>")
    sys.exit(1)

password = sys.argv[1].encode('utf-8')
hashed = bcrypt.hashpw(password, bcrypt.gensalt())
print(hashed.decode('utf-8'))

