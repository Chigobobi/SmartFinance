# wsgi.py
import sys
import os

# Tambahkan path aplikasi ke sys.path
path = '/home/haren'
if path not in sys.path:
    sys.path.append(path)

# Import aplikasi Flask
from app import app as application