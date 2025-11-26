import sys
import os
from pathlib import Path

base_dir = Path(__file__).parent.parent
sys.path.insert(0, str(base_dir))
os.chdir(str(base_dir))

from app import app, init_db
from models import db

app.config['ENV'] = 'production'

with app.app_context():
    db.create_all()
    init_db()
