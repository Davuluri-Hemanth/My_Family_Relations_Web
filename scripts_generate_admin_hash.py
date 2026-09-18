#!/usr/bin/env python3
"""Generate a bcrypt hash for ADMIN_PASSWORD_HASH."""
from getpass import getpass
from passlib.context import CryptContext

password = getpass("Admin password: ")
confirm = getpass("Confirm password: ")
if not password or password != confirm:
    raise SystemExit("Passwords are empty or do not match.")
print("\nADMIN_PASSWORD_HASH=")
print(CryptContext(schemes=["bcrypt"], deprecated="auto").hash(password))
