import sys
import os

# Add the parent directory to Python path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Vercel requires the app to be exported
def handler(request):
    return app(request.environ, lambda *args: None)