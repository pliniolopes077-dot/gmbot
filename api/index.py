import sys
import os

# Adiciona o root do repo ao Python path para que `app/` seja encontrado
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

handler = app
