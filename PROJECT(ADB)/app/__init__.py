from dotenv import load_dotenv
from flask import Flask
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
import os
import certifi

load_dotenv()
ca = certifi.where()

app = Flask(__name__, template_folder='templates', static_folder='static')
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config["MONGO_URI"] = "mongodb://localhost:27017/college-sample"
app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY")

app.jinja_env.globals.update(str=str)

app.secret_key = os.getenv("FLASK_SECRET_KEY")

mongo = PyMongo(app)
jwt = JWTManager(app)

# Import all controllers
from app.controller import admin, student, instructor, course, section, payment
# Import the new installment controller
from app.controller import installment

if __name__ == "__main__":
    app.run()
