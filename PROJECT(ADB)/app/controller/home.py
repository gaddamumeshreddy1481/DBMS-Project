from flask import render_template, request, redirect, url_for, session, flash
from app import app 
import logging
from datetime import datetime, timedelta
from bson.objectid import ObjectId 
from flask import jsonify 
from app.model.admins import Admin
from app.model.students import Student
from app.model.instructors import Instructor 



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/', methods=['GET'])
def home():
    return render_template('home.html', datetime=datetime)