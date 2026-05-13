import sys
import os

# Adiciona o root do repo ao Python path para que `app/` seja encontrado
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Google retorna escopos extras (openid, userinfo) — permite superconjunto sem erro
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from app.main import app

handler = app
