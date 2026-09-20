from flask import render_template, request, redirect, url_for, session, flash
from app import app 
import logging
from datetime import datetime, timedelta
from bson.objectid import ObjectId 
from flask import jsonify 
from app.model.admins import Admin
from app.model.students import Student
from app.model.instructors import Instructor 
from app.model.courses import Course
from app.model.sections import Section
from app.model.enrollments import Enrollment
from app.model.semesters import Semester



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




@app.route('/admin_create_semester', methods=['GET', 'POST'])
def admin_create_semester():
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))

    if request.method == 'POST':
        try:
            semester_name = request.form.get('semester_name')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            enrollment_open_date = request.form.get('enrollment_open_date')
            enrollment_close_date = request.form.get('enrollment_close_date')
            add_drop_deadline = request.form.get('add_drop_deadline')

            Semester.create(
                semester_name,
                start_date,
                end_date,
                enrollment_open_date,
                enrollment_close_date,
                add_drop_deadline
            )

            flash("Semester created successfully!", "success")
            return redirect(url_for('admin_semesters'))

        except Exception as e:
            flash(f"Failed to create semester: {str(e)}", "error")

    return render_template('admin/create_semester.html')


@app.route('/admin_semesters', methods=['GET'])
def admin_semesters():
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))

    try:
        semesters = Semester.get_all()
        return render_template('admin/view_semesters.html', semesters=semesters)
    except Exception as e:
        logger.error(f"Error fetching semesters: {str(e)}")
        flash("Failed to fetch semester data.", "error")
        return redirect(url_for('admin_home'))
