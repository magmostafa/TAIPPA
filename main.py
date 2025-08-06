import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)               # Adds /app to sys.path
sys.path.append(os.path.join(current_dir, "taippa"))  # Adds /app/taippa

from taippa.main import app
