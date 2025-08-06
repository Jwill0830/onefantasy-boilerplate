from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from firebase_admin import credentials, initialize_app, firestore
import os

# Emulator setup for local testing (points to your running emulator)
if os.environ.get('FLASK_ENV') == 'development':
    os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"  # Or 127.0.0.1:8080 if localhost fails
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ""  # No real key needed for emulator

app = Flask(__name__)
app.config.from_object('app.config.Config')

CORS(app, resources={r"/*": {"origins": "*"}})

cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
if cred_path:
    cred = credentials.Certificate(cred_path)
    initialize_app(cred)
else:
    initialize_app()  # Emulator doesn't require credentials

db = firestore.client()

socketio = SocketIO(app, cors_allowed_origins="*")

from app.routes import init_routes
init_routes(app)

from app.socket_events import init_socket_events
init_socket_events()