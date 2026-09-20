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


@app.route('/instructor_apply', methods=['GET', 'POST'])
def instructor_apply():
    if request.method == 'POST':
        email = request.form.get('email').strip()
        firstname = request.form.get('firstname').strip()
        lastname = request.form.get('lastname').strip()
        phone = request.form.get('phone').strip() 
        ssn = request.form.get('ssn').strip()
        zipcode = request.form.get('zipcode').strip()
        password = request.form.get('password').strip()
        confirm_password = request.form.get('confirm_password').strip()
        date_of_birth_str = request.form.get('date_of_birth').strip()  # mm/dd/yyyy format
        gender = request.form.get('gender').strip()
        experience = request.form.get('experience').strip()
        highest_study = request.form.get('highest_study').strip()

        if password != confirm_password:
            flash("Passwords do not match", "error")
            return redirect(url_for('instructor_apply'))

        if Instructor.exists_by_email(email):
            flash("Email already registered. Please use a different email.", "error")
            return redirect(url_for('instructor_apply'))
            
        # Parse and validate date format (mm/dd/yyyy)
        try:
            # Convert mm/dd/yyyy to datetime object
            if date_of_birth_str and '/' in date_of_birth_str:
                month, day, year = map(int, date_of_birth_str.split('/'))
                date_of_birth = datetime(year, month, day)
            else:
                flash("Invalid date format. Please use mm/dd/yyyy format.", "error")
                return redirect(url_for('instructor_apply'))
        except ValueError:
            flash("Invalid date. Please enter a valid date in mm/dd/yyyy format.", "error")
            return redirect(url_for('instructor_apply'))

        hashed_password = password
        
        # Construct full name from first and last name
        name = f"{firstname} {lastname}"
        
        data = {
            "name": name,
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "phone": phone,
            "ssn": ssn,
            "zipcode": zipcode,
            "password": hashed_password,
            "date_of_birth": date_of_birth,  # Store as datetime object
            "gender": gender,
            "experience": int(experience),
            "highest_study": highest_study,
            "status": "pending",
            "authorization_status": "unauthorized"
        }

        Instructor.create(data)
        return redirect(url_for('instructor_signin'))
    return render_template('instructor/apply.html')



@app.route('/instructor_signin', methods=['GET', 'POST'])
def instructor_signin():
    if request.method == 'POST':
        email = request.form.get("email").strip()
        password = request.form.get("password").strip()

        if Instructor.exists_by_email(email):
            instructor = Instructor.get_by_email(email)
            if instructor['status'] == "approved" and instructor['authorization_status'] == "authorized" and (instructor['password'] == password):
                session["user_id"] = str(instructor['_id'])
                session["user_type"] = "instructor"
                return redirect(url_for('instructor_home'))
            elif instructor['status'] == "approved" and instructor['authorization_status'] != "authorized":
                return "Your account is not authorized yet. Please contact the administrator.", 400
            else:
                return "Application pending or invalid credentials", 400
        else:
            return "No such instructor", 404
    return render_template('instructor/signin.html')

@app.route('/instructor_home')
def instructor_home():
    if session.get("user_type") != "instructor":
        flash("Unauthorized access.", "error")
        return redirect(url_for('instructor_signin'))

    try:
        instructor_id = session.get("user_id")
        instructor = Instructor.get_by_id(ObjectId(instructor_id))
        
        if not instructor:
            flash("Instructor data not found.", "error")
            return redirect(url_for('instructor_signin'))
        
        # Get all sections assigned to this instructor with course details
        current_sections_list = Section.get_by_instructor_with_course_details(instructor_id)
        
        # Count total enrolled students across all sections
        enrolled_students = 0
        for section in current_sections_list:
            section_id = str(section.get('_id', ''))
            # Convert ObjectId to string for template use
            section['id'] = section_id
            # Get enrolled student count for this section
            enrolled_count = Enrollment.get_enrollment_count_by_section(section_id)
            section['enrolled_students'] = enrolled_count
            enrolled_students += enrolled_count
            
            # Get semester name if available
            if 'semester_id' in section:
                semester = Semester.get_by_id(section['semester_id'])
                section['semester'] = semester.get('name', 'Unknown') if semester else 'Unknown'
            else:
                section['semester'] = 'Current'
        
        return render_template('instructor/home.html',
                              instructor_name=instructor.get('name', ''),
                              instructor_department=instructor.get('department', ''),
                              current_sections=len(current_sections_list),
                              enrolled_students=enrolled_students,
                              current_sections_list=current_sections_list)
    except Exception as e:
        logger.error(f"Error loading instructor home: {e}")
        flash("An error occurred while loading the dashboard.", "error")
        return redirect(url_for('instructor_signin'))


@app.route('/instructor_logout')
def instructor_logout():
    session.clear()
    return redirect(url_for('instructor_signin'))

# instructor_section_details
@app.route('/instructor_section_details/<section_id>')
def instructor_section_details(section_id):
    if session.get("user_type") != "instructor":
        flash("Unauthorized access.", "error")
        return redirect(url_for('instructor_signin'))
    
    section = Section.get_by_id(ObjectId(section_id))
    course = Course.get_by_id(section['course_id'])
    return render_template('instructor/section_details.html', section=section, course=course)




@app.route('/instructor_students/<section_id>')
def instructor_students(section_id):
    if session.get("user_type") != "instructor":
        flash("Unauthorized access.", "error")
        return redirect(url_for('instructor_signin'))

    try:
        enrollments = Enrollment.get_students_by_section(ObjectId(section_id))
        student_ids = [enr['student_id'] for enr in enrollments]
        students = Student.get_by_ids(student_ids)

        return render_template("instructor/students.html", students=students)
    except Exception as e:
        logger.error(f"Error loading students for section {section_id}: {str(e)}")
        flash("Could not load student list.", "error")
        return redirect(url_for("instructor_home"))
