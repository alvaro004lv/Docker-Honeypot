import sys
import os

# Agregar la carpeta de la aplicación al path
sys.path.insert(0, '/var/www/html')

from main import app as application
