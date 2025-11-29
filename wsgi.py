"""WSGI entry point for gunicorn."""
from backend.app import create_app
import os

config_path = os.getenv('PHOTOMEDIT_CONFIG', 'config.yaml')
application = create_app(config_path)

if __name__ == '__main__':
    application.run()

