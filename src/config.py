import os

# Absolute path to the directory where this config.py file is located
# This is to ensure that paths are correct regardless of where the app is run from
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to the 'db' directory inside 'src'
DB_DIR = os.path.join(APP_DIR, "db")

REPLACEMENTS_DB   = os.path.join(DB_DIR, "استبدالات.db")
DB_PATH           = os.path.join(DB_DIR, "البحور.db") # This was 'meters.db' effectively in core.py
WEIGHTS_DB        = os.path.join(DB_DIR, "أوزان البحور.db")
TAFEELAT_DB       = os.path.join(DB_DIR, "الزحافات والعلل.db")

# OUTPUT_FILE is not needed for the web app as results are sent to the frontend

