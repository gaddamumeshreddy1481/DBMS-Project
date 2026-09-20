from flask import render_template, request, redirect, url_for, session, flash
from app import app 
import logging
from datetime import datetime, timedelta
from bson.objectid import ObjectId 
from flask import jsonify 
from app.model.admins import Admin
from app.model.students import Student
from app.model.courses import Course
from app.model.instructors import Instructor
from app.model.enrollments import Enrollment
from app.model.sections import Section



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



@app.route('/admin_manage_courses', methods=['GET', 'POST'])
def admin_manage_courses():
    # Uncomment the following lines if session control is needed
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))

    if request.method == 'POST':
        # Handling the addition of a new course
        course_name = request.form.get('course_name')
        course_code = request.form.get('course_code')
        course_credit = request.form.get('course_credit')
        course_description = request.form.get('course_description')
        # class_days = request.form.get('class_days')
        # time_slot = request.form.get('time_slot')

        # Create a dictionary with the new course data
        data = {
            'course_name': course_name,
            'course_code': course_code,
            'course_credit': course_credit,
            'course_description': course_description,
            'created_at': datetime.now(),
            # 'class_days': class_days,
            # 'time_slot': time_slot
        }

        # Attempt to create a new course using the provided data
        try:
            Course.create(data)
            flash('Course added successfully', 'success')
            return redirect(url_for('admin_manage_courses'))  # Redirect after POST
        except Exception as e:
            flash(f'Failed to add course: {str(e)}', 'error')
            return redirect(url_for('admin_manage_courses'))  # Redirect after POST to clear form data

    # Fetch all courses to display on the page for GET request
    try:
        courses = Course.get_all()
        courses = list(courses)
    except Exception as e:
        flash(f'Failed to fetch courses: {str(e)}', 'error')
        courses = []

    return render_template('admin/admin_manage_courses.html', courses=courses)

