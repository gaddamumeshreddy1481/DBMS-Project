
from flask import render_template, request, redirect, url_for, session, flash
from app import app
import os
import logging
from datetime import datetime, timedelta
from bson.objectid import ObjectId 
from flask import jsonify 
from app.model.admins import Admin
from app.model.students import Student
from app.model.instructors import Instructor
from app.model.semesters import Semester
from app.model.sections import Section
from app.model.courses import Course
from app.model.enrollments import Enrollment



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/admin_create', methods=['GET'])
def admin_create():
    try:
        # Hard-coded admin data
        email = os.getenv("ADMIN_EMAIL")
        user_name = "Admin User"
        phone = "999-000-7890"
        password = os.getenv("ADMIN_PASSWORD")

        # Check if the admin email is already registered
        if Admin.exists_by_email(email):
            return jsonify({"message": "Admin already registered. Check DB for details."}), 200

        # Data preparation
        data = {
            "user_name": user_name,
            "email": email,
            "phone": phone,
            "password": password
        }

        # Create admin record
        Admin.create(data)
        return jsonify({"message": "Admin registered successfully!"}), 201

    except Exception as e:
        logger.error(f"Error during admin registration: {str(e)}")
        return "Internal Server Error", 500



@app.route('/admin_signin', methods=['GET', 'POST'])
def admin_signin():
    if request.method == 'POST':
        email = request.form.get("email").strip()
        password = request.form.get("password").strip()
        
        # Check if user exists in the admin database
        if Admin.exists_by_email(email):
            admin = Admin.get_by_email(email)
            if (admin['password'] == password):
                session["user_id"] = str(admin['_id'])
                session["user_type"] = "admin"
                return redirect(url_for('admin_home'))
            else:
                return "Invalid credentials", 400
        else:
            return "No such admin", 404

    return render_template('admin/signin.html')


@app.route('/admin_home')
def admin_home():
    if session["user_type"] != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin')) 
    return render_template('admin/home.html')


@app.route('/admin_logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_signin'))


@app.route('/admin_all_students', methods=['GET', 'POST'])
def admin_all_students():
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))

    try:
        students = list(Student.get_all())  # Fetch all students
        sections = list(Section.get_all())  # Fetch all sections for dropdown

        if request.method == 'POST':
            student_id = request.form.get('student_id')
            section_id = request.form.get('course_id')

            # Convert to ObjectId
            student_obj_id = ObjectId(student_id)
            section_obj_id = ObjectId(section_id) if section_id else None

            if Enrollment.create({'student_id': student_obj_id, 'section_id': section_obj_id}):
                flash("Course assigned successfully!", "success")
            else:
                flash("Failed to assign course.", "error")
            return redirect(url_for('admin_all_students'))

        # Optionally, attach course names to students for display
        for student in students:
            course_names = Enrollment.get_course_name_by_student_id(student['_id'])
            student['course_name'] = ', '.join(course_names) if course_names else "No course assigned"

        return render_template('admin/all_students.html', students=students, sections=sections)
    except Exception as e:
        logger.error(f"Error managing students: {str(e)}")
        flash("Failed to manage students.", "error")
        return redirect(url_for('admin_home'))
    

@app.route('/admin_pending_students')
def admin_pending_students():
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))

    try:
        pending_students = Student.get_by_status("pending")  # Adjust this method to suit your model
        pending_students = list(pending_students)
        return render_template('admin/pending_students.html', students=pending_students)
    except Exception as e:
        logger.error(f"Error fetching pending students: {str(e)}")
        flash("Failed to fetch pending student data.", "error")
        return redirect(url_for('admin_home'))

from bson import ObjectId

@app.route('/admin_approved_instructors', methods=['GET', 'POST'])
def admin_approved_instructors():
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))

    try:
        approved_instructors = Instructor.get_by_status("approved")
        approved_instructors = list(approved_instructors)
        all_courses = list(Course.get_all())
        
        # Process course assignments for each instructor
        for instructor in approved_instructors:
            course_names = Section.get_course_name_by_instructor_id(instructor['_id'])
            instructor['course_name'] = ', '.join(course_names) if course_names else "No course assigned"
            instructor['assigned_courses'] = Section.get_by_instructor_with_course_details(str(instructor['_id']))
            
            # Set default authorization status if not present
            if 'authorization_status' not in instructor:
                instructor['authorization_status'] = 'unauthorized'
        
        # Handle POST request for course assignment
        if request.method == 'POST':
            instructor_id = request.form.get('instructor_id')
            course_id = request.form.get('course_id')
            action = request.form.get('action', 'add')  # Default action is add

            if not instructor_id:
                flash("Invalid instructor selection.", "error")
                return redirect(url_for('admin_approved_instructors'))

            instructor_obj_id = ObjectId(instructor_id)
            
            # If removing a course assignment
            if action == 'remove' and course_id:
                # Find the specific section for this instructor and course
                sections = Section.get_by_instructor_id(str(instructor_obj_id))
                for section in sections:
                    if str(section.get('course_id')) == course_id:
                        Section.delete(str(section['_id']))
                        flash("Course assignment removed successfully!", "success")
                        break
                return redirect(url_for('admin_approved_instructors'))
            
            # If adding a new course assignment
            if action == 'add' and course_id:
                course_obj_id = ObjectId(course_id)
                
                # Check if this course is already assigned to this instructor
                sections = Section.get_by_instructor_id(str(instructor_obj_id))
                for section in sections:
                    if str(section.get('course_id')) == str(course_obj_id):
                        flash("This course is already assigned to this instructor.", "error")
                        return redirect(url_for('admin_approved_instructors'))
                
                # Create new section with the selected course
                data = {
                    'instructor_id': instructor_obj_id,
                    'course_id': course_obj_id,
                    'max_students': 30,  # Default value
                    'date': datetime.now(), 
                    'status': 'active'
                }

                if Section.create_section(data):
                    flash("Course assigned successfully!", "success")
                else:
                    flash("Failed to assign course.", "error")
            
            return redirect(url_for('admin_approved_instructors'))

        # Get all available courses for the dropdown
        semesters = Semester.get_all()
        semesters = list(semesters)
        return render_template('admin/approved_instructors.html', instructors=approved_instructors, available_courses=all_courses, semesters=semesters)
    except Exception as e:
        logger.error(f"Error fetching approved instructors: {str(e)}")
        flash("Failed to fetch approved instructor data.", "error")
        return redirect(url_for('admin_home'))


@app.route('/admin_pending_instructors')
def admin_pending_instructors():
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))

    try:
        pending_instructors = Instructor.get_by_status("pending")
        pending_instructors = list(pending_instructors)
        return render_template('admin/pending_instructors.html', instructors=pending_instructors)
    except Exception as e:
        logger.error(f"Error fetching pending instructors: {str(e)}")
        flash("Failed to fetch pending instructor data.", "error")
        return redirect(url_for('admin_home'))


@app.route('/admin_instructor_authorization')
def admin_instructor_authorization():
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))

    try:
        # Get approved instructors to manage their authorization
        approved_instructors = Instructor.get_by_status("approved")
        approved_instructors = list(approved_instructors)
        return render_template('admin/instructor_authorization.html', instructors=approved_instructors)
    except Exception as e:
        logger.error(f"Error fetching instructors for authorization: {str(e)}")
        flash("Failed to fetch instructor data.", "error")
        return redirect(url_for('admin_home'))


@app.route('/instructor_approve/<instructor_id>', methods=['POST'])
def instructor_approve(instructor_id):
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))

    try:
        status = request.form.get('status')
        reason = request.form.get('reason', '').strip()

        if status == 'approved':
            # Set both status and authorization status to approved/authorized
            Instructor.update_status(instructor_id, status)
            Instructor.update_authorization_status(instructor_id, "authorized")
            flash("Instructor approved and authorized successfully!", "success")
        elif status == 'rejected':
            Instructor.update_status(instructor_id, status, reason=reason)
            flash("Instructor rejected successfully!", "success")
        else:
            flash("Invalid status update.", "error")

        return redirect(url_for('admin_pending_instructors'))
    except Exception as e:
        logger.error(f"Error updating instructor status: {str(e)}")
        flash("Failed to update instructor status.", "error")
        return redirect(url_for('admin_pending_instructors'))


@app.route('/instructor_authorize/<instructor_id>', methods=['POST'])
def instructor_authorize(instructor_id):
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))

    try:
        authorization_status = request.form.get('authorization_status')
        reason = request.form.get('reason', '').strip()

        if authorization_status == 'authorized':
            Instructor.update_authorization_status(instructor_id, authorization_status)
            flash("Instructor authorized successfully!", "success")
        elif authorization_status == 'unauthorized':
            Instructor.update_authorization_status(instructor_id, authorization_status, reason=reason)
            flash("Instructor unauthorized successfully!", "success")
        else:
            flash("Invalid authorization status update.", "error")

        return redirect(url_for('admin_instructor_authorization'))
    except Exception as e:
        logger.error(f"Error updating instructor authorization status: {str(e)}")
        flash("Failed to update instructor authorization status.", "error")
        return redirect(url_for('admin_instructor_authorization'))



@app.route('/student_approve/<student_id>', methods=['POST'])
def student_approve(student_id):
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))

    try:
        status = request.form.get('status')
        reason = request.form.get('reason', '').strip()

        if status == 'approved':
            Student.update_status(student_id, status)
            flash("Student approved successfully!", "success")
        elif status == 'rejected':
            Student.update_status(student_id, status, reason=reason)
            flash("Student rejected successfully!", "success")
        else:
            flash("Invalid status update.", "error")

        return redirect(url_for('admin_pending_students'))
    except Exception as e:
        logger.error(f"Error updating student status: {str(e)}")
        flash("Failed to update student status.", "error")
        return redirect(url_for('admin_pending_students'))



# admin_courses
@app.route('/admin_courses', methods=['GET', 'POST'])
def admin_courses():
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))

    try:
        courses = list(Course.get_all())
        return render_template('admin/courses.html', courses=courses)
    except Exception as e:
        logger.error(f"Error fetching courses: {str(e)}")
        flash("Failed to fetch course data.", "error")
        return redirect(url_for('admin_home'))



# admin_enrollments
@app.route('/admin_enrollments', methods=['GET', 'POST'])
def admin_enrollments():
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))

    try:
        # Get filter parameters
        status_filter = request.args.get('status')
        course_id_filter = request.args.get('course_id')
        
        # Apply filters if provided
        query = {}
        if status_filter:
            query['status'] = status_filter
        if course_id_filter:
            query['course_id'] = ObjectId(course_id_filter)
            
        # Get enrollments with applied filters
        enrollments = list(Enrollment.get_all(query))
        
        # Fetch related data for display
        for enrollment in enrollments:
            # Get student information
            student = Student.get_by_id(enrollment.get('student_id'))
            enrollment['student_name'] = student.get('name') if student else 'Unknown Student'
            
            # Get section and course information
            section = Section.get_by_id(enrollment.get('section_id'))
            if section:
                course = Course.get_by_id(section.get('course_id'))
                enrollment['course_name'] = course.get('course_name') if course else 'Unknown Course'
                enrollment['section_details'] = f"Section {section.get('_id')}"
            else:
                enrollment['course_name'] = 'Unknown Course'
                enrollment['section_details'] = 'Unknown Section'
        
        # Get all courses for the filter dropdown
        courses = list(Course.get_all())
        
        return render_template('admin/enrollments.html', enrollments=enrollments, courses=courses)
    except Exception as e:
        logger.error(f"Error fetching enrollments: {str(e)}")
        flash("Failed to fetch enrollment data.", "error")
        return redirect(url_for('admin_home'))

# Add a route to update enrollment status
@app.route('/admin/update_enrollment/<enrollment_id>', methods=['POST'])
def admin_update_enrollment_status(enrollment_id):
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))
        
    try:
        status = request.form.get('status')
        drop_reason = request.form.get('drop_reason', '')
        payment_status = request.form.get('payment_status')
        
        # Update enrollment status
        update_data = {
            'status': status
        }
        
        if drop_reason and status == 'dropped':
            update_data['drop_reason'] = drop_reason
            
        if payment_status:
            update_data['payment_status'] = payment_status
            
        Enrollment.update(enrollment_id, update_data)
        flash("Enrollment updated successfully!", "success")
    except Exception as e:
        logger.error(f"Error updating enrollment: {str(e)}")
        flash(f"Failed to update enrollment: {str(e)}", "error")
        
    return redirect(url_for('admin_enrollments'))
