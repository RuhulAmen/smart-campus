import os
import sys

# Add project root and backend directory to sys.path so app, models, and routes resolve
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

backend_dir = os.path.join(root_dir, 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Expose the Flask instance as 'app' for Vercel's serverless Python runtime
from app import app  # type: ignore

