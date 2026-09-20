from flask import render_template, request, redirect, url_for, session, flash
from app import app 
import logging
from datetime import datetime, timedelta
from bson.objectid import ObjectId 
from flask import jsonify 
from app.model.admins import Admin
from app.model.students import Student
from app.model.instructors import Instructor 
from app.model.semesters import Semester
from app.model.payments import Payment
from app.model.enrollments import Enrollment
from app.model.sections import Section
from app.model.courses import Course



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/student_apply', methods=['GET', 'POST'])
def student_apply():
    if request.method == 'POST':
        email = request.form.get('email').strip()
        firstname = request.form.get('firstname').strip()
        lastname = request.form.get('lastname').strip()
        password = request.form.get('password').strip()
        confirm_password = request.form.get('confirm_password').strip()
        date_of_birth_str = request.form.get('date_of_birth').strip()  # mm/dd/yyyy format
        gender = request.form.get('gender').strip()
        zipcode = request.form.get('zipcode').strip()

        if password != confirm_password:
            flash("Passwords do not match", "error")
            return redirect(url_for('student_apply'))

        if Student.exists_by_email(email):
            flash("Email already registered. Please use a different email.", "error")
            return redirect(url_for('student_apply'))
            
        # Parse and validate date format (mm/dd/yyyy)
        try:
            # Convert mm/dd/yyyy to datetime object
            if date_of_birth_str and '/' in date_of_birth_str:
                month, day, year = map(int, date_of_birth_str.split('/'))
                date_of_birth = datetime(year, month, day)
            else:
                flash("Invalid date format. Please use mm/dd/yyyy format.", "error")
                return redirect(url_for('student_apply'))
        except ValueError:
            flash("Invalid date. Please enter a valid date in mm/dd/yyyy format.", "error")
            return redirect(url_for('student_apply'))

        hashed_password = password
        
        # Construct full name from first and last name
        name = f"{firstname} {lastname}"
        
        data = {
            "name": name,
            "firstname": firstname,
            "lastname": lastname,
            "email": email, 
            "password": hashed_password,
            "date_of_birth": date_of_birth,  # Store as datetime object
            "gender": gender,
            "zipcode": zipcode,
            "status": "approved"  # Set status to approved by default
        }

        Student.create(data)
        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for('student_signin'))
    return render_template('student/apply.html')


@app.route('/student_signin', methods=['GET', 'POST'])
def student_signin():
    if request.method == 'POST':
        email = request.form.get("email").strip()
        password = request.form.get("password").strip()

        if Student.exists_by_email(email):
            student = Student.get_by_email(email)
            if student['password'] == password:  # Students are automatically approved now
                session["user_id"] = str(student['_id'])
                session["user_type"] = "student"
                return redirect(url_for('student_home'))
            else:
                flash("Invalid credentials. Please try again.", "error")
                return redirect(url_for('student_signin'))
        else:
            flash("No account found with that email. Please register first.", "error")
            return redirect(url_for('student_signin'))
    return render_template('student/signin.html')



@app.route('/student_home')
def student_home():
    if session.get("user_type") != "student":
        flash("Unauthorized access.", "error")
        return redirect(url_for('student_signin'))
    return render_template('student/home.html')


@app.route('/student_logout')
def student_logout():
    session.clear()
    return redirect(url_for('student_signin'))



from datetime import datetime, timezone



@app.route('/student_select_semester', methods=['GET', 'POST'])
def student_select_semester():
    if session.get("user_type") != "student":
        flash("Unauthorized access.", "error")
        return redirect(url_for('student_signin'))
    
    try:
        # Get all active semesters
        all_semesters = list(Semester.get_all())
        active_semesters = []
        now = datetime.utcnow()
        
        for semester in all_semesters:
            # Check if enrollment is currently open
            if 'enrollment_open_date' in semester and 'enrollment_close_date' in semester:
                if semester['enrollment_open_date'] <= now <= semester['enrollment_close_date']:
                    semester['status'] = 'Open for enrollment'
                    semester['is_active'] = True
                elif now < semester['enrollment_open_date']:
                    semester['status'] = f"Opens {semester['enrollment_open_date'].strftime('%b %d, %Y')}"
                    semester['is_active'] = False
                else:
                    semester['status'] = f"Closed on {semester['enrollment_close_date'].strftime('%b %d, %Y')}"
                    semester['is_active'] = False
                
                # Convert ObjectId to string for template
                semester['id'] = str(semester['_id'])
                active_semesters.append(semester)
        
        if request.method == 'POST':
            semester_id = request.form.get('semester_id')
            if semester_id:
                return redirect(url_for('student_register_courses', semester_id=semester_id))
            else:
                flash("Please select a semester", "error")
        
        return render_template("student/select_semester.html", semesters=active_semesters)
    
    except Exception as e:
        logger.error(f"Error loading semesters: {str(e)}")
        flash(f"Something went wrong: {str(e)}", "error")
        return render_template("student/select_semester.html", semesters=[])


@app.route('/student_register_courses/<semester_id>', methods=['GET', 'POST'])
def student_register_courses(semester_id):
    if session.get("user_type") != "student":
        flash("Unauthorized access.", "error")
        return redirect(url_for('student_signin'))

    try:
        student_id = session.get("user_id")
        current_semester = Semester.get_by_id(semester_id)
        if not current_semester:
            flash("Invalid semester.", "error")
            return redirect(url_for('student_select_semester'))
        
        # Get previous semester courses
        previous_semester_courses = []
        if 'start_date' in current_semester:
            previous_semester = Semester.get_previous_semester(current_semester['start_date'])
            if previous_semester:
                prev_enrollments = Enrollment.get_active_enrollments_by_semester(
                    student_id, 
                    str(previous_semester['_id'])
                )
                for enrollment in prev_enrollments:
                    section = Section.get_by_id(enrollment['section_id'])
                    if not section:
                        continue
                    course = Course.get_by_id(section['course_id'])
                    if course:
                        previous_semester_courses.append(course)
        
        # Get sections for the selected semester
        all_sections = list(Section.get_by_semester_id(semester_id))
        enrollments = Enrollment.get_active_enrollments(student_id)
        enrolled_course_ids = set()
        enrolled_course_names = set()
        enrolled_section_ids = [str(e['section_id']) for e in enrollments]
        enrolled_section_schedules = []
        enrolled_section_id_to_enrollment_id = {}
        for enrollment in enrollments:
            section = Section.get_by_id(enrollment['section_id'])
            if section:
                course = Course.get_by_id(section['course_id'])
                if course:
                    enrolled_course_ids.add(str(section['course_id']))
                    enrolled_course_names.add(course['course_name'])
                enrolled_section_schedules.append(section['schedule'])
                enrolled_section_id_to_enrollment_id[str(section['_id'])] = str(enrollment['_id'])
        
        # Process sections with seat availability
        eligible_sections = []
        ineligible_sections = []
        for section in all_sections:
            course = Course.get_by_id(section['course_id'])
            if not course:
                continue
            instructor = Instructor.get_by_id(section['instructor_id'])
            instructor_name = instructor['name'] if instructor and 'name' in instructor else 'Unknown'
            # Calculate available seats
            total_seats = section.get('seat_capacity', 30)
            current_enrollments = Enrollment.get_enrollment_count_by_section(str(section['_id']))
            available_seats = total_seats - current_enrollments
            # Build classroom info
            classroom_info = ""
            # Check if room_number exists directly in the section document
            if section.get('room_number'):
                classroom_info = f"Room {section['room_number']}"
            # For backward compatibility, also check the classroom object if it exists
            elif section.get('classroom'):
                room = section['classroom'].get('room_number')
                building = section['classroom'].get('building')
                if room:
                    classroom_info = f"Room {room}"
                if building:
                    classroom_info = f"{building} {classroom_info}".strip()
            # Build section info
            section_info = {
                '_id': str(section['_id']),
                'section_id': section['section_id'],
                'course_name': course['course_name'],
                'course_code': course['course_code'],
                'course_credit': course.get('credit_hours', 3),
                'schedule': section['schedule'],
                'classroom': classroom_info if classroom_info else "TBA",
                'available_seats': available_seats,
                'total_seats': total_seats,
                'is_enrolled': str(section['_id']) in enrolled_section_ids,
                'instructor_name': instructor_name
            }
            # Add enrollment_id for drop
            if str(section['_id']) in enrolled_section_id_to_enrollment_id:
                section_info['enrollment_id'] = enrolled_section_id_to_enrollment_id[str(section['_id'])]
            # Check for schedule conflict with any enrolled section
            has_conflict = False
            if not section_info['is_enrolled']:
                for sched in enrolled_section_schedules:
                    if schedules_conflict(section['schedule'], sched):
                        has_conflict = True
                        break
            # Check eligibility
            if section_info['is_enrolled']:
                section_info['reason'] = "Already enrolled in this section"
                ineligible_sections.append(section_info)
            elif has_conflict:
                section_info['reason'] = "Schedule conflict"
                ineligible_sections.append(section_info)
            elif course['course_name'] in enrolled_course_names:
                section_info['reason'] = "Course name conflict: Already enrolled in a section of this course (by name)"
                ineligible_sections.append(section_info)
            elif available_seats <= 0:
                section_info['reason'] = "No available seats"
                ineligible_sections.append(section_info)
            elif datetime.utcnow() < current_semester['enrollment_open_date']:
                section_info['reason'] = f"Enrollment opens {current_semester['enrollment_open_date'].strftime('%b %d, %Y')}"
                ineligible_sections.append(section_info)
            elif datetime.utcnow() > current_semester['enrollment_close_date']:
                section_info['reason'] = f"Enrollment closed on {current_semester['enrollment_close_date'].strftime('%b %d, %Y')}"
                ineligible_sections.append(section_info)
            else:
                eligible_sections.append(section_info)
        
        return render_template(
            "student/register_courses.html",
            semester=current_semester,
            semester_id=semester_id,
            all_sections=eligible_sections + ineligible_sections,
            previous_semester_courses=previous_semester_courses,
            conflict_rules=[
                "You cannot register for more than 3 courses or 9 credits per semester.",
                "You cannot register for two sections of the same course (by course name) in the same semester.",
                "You cannot register for sections with schedule conflicts.",
                "You cannot register for a section that is full."
            ]
        )
        
    except Exception as e:
        logger.error(f"Error in student_register_courses: {str(e)}")
        flash("An error occurred while loading courses.", "error")
        return redirect(url_for('student_select_semester'))




@app.route('/student_drop_course_enroll_page', methods=['POST'])
def student_drop_course_enroll_page():
    if session.get("user_type") != "student":
        flash("Unauthorized access.", "error")
        return redirect(url_for('student_signin'))

    section_id = request.form.get("section_id")
    student_id = session.get("user_id")

    enrollment = Enrollment.get_by_student_and_section(student_id, section_id)
    if enrollment:
        # Get the section to determine the semester_id for redirect
        section = Section.get_by_id(section_id)
        semester_id = str(section['semester_id']) if section and 'semester_id' in section else None
        # Delete the enrollment record completely
        Enrollment.collection.delete_one({'_id': enrollment['_id']})
        # Update available seats
        Section.increment_available_seats(section_id)
        flash("Course dropped successfully.", "success")
    else:
        flash("Enrollment not found.", "error")

    # Redirect to semester selection if we couldn't determine the semester
    if not semester_id:
        return redirect(url_for('student_select_semester'))
    
    return redirect(url_for('student_register_courses', semester_id=semester_id))


def schedules_conflict(schedule1, schedule2):
    # Both schedules are lists of dicts
    for item1 in schedule1:
        for item2 in schedule2:
            if item1['day'] == item2['day']:
                # Compare times
                start1 = datetime.strptime(item1['start_time'], '%H:%M')
                end1 = datetime.strptime(item1['end_time'], '%H:%M')
                start2 = datetime.strptime(item2['start_time'], '%H:%M')
                end2 = datetime.strptime(item2['end_time'], '%H:%M')
                if start1 < end2 and end1 > start2:
                    return True
    return False


@app.route('/student_register_course/<semester_id>', methods=['POST'])
def student_register_course(semester_id):
    if session.get("user_type") != "student":
        flash("Unauthorized access.", "error")
        return redirect(url_for('student_signin'))

    try:
        student_id = session.get("user_id")
        section_id = request.form.get('section_id')
        section = Section.get_by_id(section_id)

        if not section:
            flash("Section not found.", "error")
            return redirect(url_for('student_register_courses', semester_id=semester_id))

        semester = Semester.get_by_id(section['semester_id'])
        if not semester:
            flash("Semester not found.", "error")
            return redirect(url_for('student_register_courses', semester_id=semester_id))

        now = datetime.now(timezone.utc)
        for key in ['enrollment_open_date', 'enrollment_close_date']:
            if semester[key].tzinfo is None:
                semester[key] = semester[key].replace(tzinfo=timezone.utc)

        if not (semester['enrollment_open_date'] <= now <= semester['enrollment_close_date']):
            flash("Enrollment window is closed.", "error")
            return redirect(url_for('student_register_courses', semester_id=semester_id))

        existing = Enrollment.get_by_student_and_section(student_id, section_id)
        if existing and existing['status'] == 'active':
            flash("Already enrolled in this section.", "error")
            return redirect(url_for('student_register_courses', semester_id=semester_id))

        current_enrollments = Enrollment.get_active_enrollments_by_semester(student_id, str(semester['_id']))
        
        # Check for minimum/maximum credits
        current_credits = 0
        for enrollment in current_enrollments:
            enrolled_section = Section.get_by_id(enrollment['section_id'])
            if enrolled_section:
                course = Course.get_by_id(enrolled_section['course_id'])
                if course and 'credit_hours' in course:
                    current_credits += course['credit_hours']
        
        # Get credits for the new course
        course = Course.get_by_id(section['course_id'])
        new_course_credits = course.get('credit_hours', 3) if course else 3
        
        # Check maximum credits (9) and maximum courses (3)
        if current_credits + new_course_credits > 9:
            flash(f"Exceeds maximum credits (9). Current: {current_credits}, Adding: {new_course_credits}", "error")
            return redirect(url_for('student_register_courses', semester_id=semester_id))
        if len(current_enrollments) >= 3:
            flash("You cannot enroll in more than 3 courses in this semester.", "error")
            return redirect(url_for('student_register_courses', semester_id=semester_id))

        # Check for time conflicts with more detailed messages
        conflict_courses = []
        for enrollment in current_enrollments:
            enrolled_section = Section.get_by_id(enrollment['section_id'])
            if enrolled_section and schedules_conflict(enrolled_section['schedule'], section['schedule']):
                # Get the conflicting course name
                conflict_course = Course.get_by_id(enrolled_section['course_id'])
                if conflict_course:
                    conflict_courses.append({
                        'name': conflict_course.get('course_name', 'Unknown Course'),
                        'code': conflict_course.get('course_code', ''),
                        'schedule': enrolled_section.get('schedule', 'Unknown Schedule')
                    })
        
        if conflict_courses:
            conflict_details = ', '.join([f"{c['name']} ({c['code']}) at {c['schedule']}" for c in conflict_courses])
            flash(f"Schedule conflict detected with: {conflict_details}", "error")
            return redirect(url_for('student_register_courses', semester_id=semester_id))

        Enrollment.create(student_id, section_id, str(semester['_id']))
        Section.decrement_available_seats(section_id)

        Payment.create_or_update_unpaid(student_id, section_id, course_fee=100.0)

        flash("Enrolled successfully!", "success")
        return redirect(url_for('student_register_courses', semester_id=semester_id))

    except Exception as e:
        logger.error(f"Enrollment failed: {str(e)}")
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('student_register_courses', semester_id=semester_id))










@app.route('/student_view_enrollments')
def student_view_enrollments():
    if session.get("user_type") != "student":
        flash("Unauthorized access.", "error")
        return redirect(url_for('student_signin'))
        
    student_id = session.get("user_id")
    
    try:
        # Get all active enrollments for the student
        enrollments = Enrollment.get_active_enrollments(student_id)
        
        # Add debug logging
        logger.info(f"Found {len(enrollments)} active enrollments for student {student_id}")
        
        # Prepare data for display
        enrollment_details = []
        for enrollment in enrollments:
            logger.info(f"Processing enrollment: {enrollment}")
            
            # Get section details
            section_id = str(enrollment['section_id'])
            section = Section.get_by_id(section_id)
            
            if not section:
                logger.warning(f"Section not found for ID: {section_id}")
                continue
                
            logger.info(f"Found section: {section}")
            
            # Get course details
            course_id = str(section.get('course_id'))
            logger.info(f"Looking up course with ID: {course_id}")
            course = Course.get_by_id(course_id)
            
            if not course:
                logger.warning(f"Course not found for ID: {course_id}")
                # Use a placeholder course object instead of skipping
                course = {
                    'course_name': f"Unknown Course ({course_id})",
                    'course_code': 'Unknown'
                }
                
            
            # Check payment status
            payment_status = "Unpaid"
            
            # First check if there's a direct payment for this section
            payment = Payment.collection.find_one({
                'student_id': ObjectId(student_id),
                'courses': {'$in': [ObjectId(section_id)]},
                'status': 'paid'
            })
            
            if not payment:
                # Try alternative query formats
                logger.info(f"Trying alternative payment query formats for section {section_id}")
                
                # Check if section_id is in the courses array as a string
                payment = Payment.collection.find_one({
                    'student_id': ObjectId(student_id),
                    'status': 'paid',
                    'courses': section_id
                })
                
                if not payment:
                    # Check all paid payments and log their courses for debugging
                    paid_payments = list(Payment.collection.find({
                        'student_id': ObjectId(student_id),
                        'status': 'paid'
                    }))
                    
                    logger.info(f"Found {len(paid_payments)} paid payments for student {student_id}")
                    for p in paid_payments:
                        logger.info(f"Paid payment {p['_id']} has courses: {p.get('courses', [])}")
                        
                        # Check if any of the courses in this payment match our section
                        if 'courses' in p:
                            courses = p['courses']
                            logger.info(f"Checking courses: {courses}")
                            for course_entry in courses:
                                course_str = str(course_entry)
                                logger.info(f"Comparing {course_str} with {section_id}")
                                if course_str == section_id:
                                    payment = p
                                    logger.info(f"Found matching course in payment {p['_id']}")
                                    break
            
            if payment:
                payment_status = "Paid"
                logger.info(f"Found paid payment for section {section_id}: {payment}")
            else:
                logger.info(f"No paid payment found for section {section_id}")
            
            logger.info(f"Final payment status for section {section_id}: {payment_status}")
            
            # Format schedule for display
            schedule_display = "Unknown"
            if isinstance(section.get('schedule'), str):
                schedule_display = section.get('schedule')
            elif isinstance(section.get('schedule'), dict):
                schedule_parts = []
                for day, times in section.get('schedule').items():
                    time_strs = []
                    for time_slot in times:
                        time_strs.append(f"{time_slot.get('start', '?')} - {time_slot.get('end', '?')}")
                    schedule_parts.append(f"{day}: {', '.join(time_strs)}")
                schedule_display = "; ".join(schedule_parts)
                        # Get semester information for add/drop deadline
            semester_id = str(section.get('semester_id')) if 'semester_id' in section else None
            can_drop = False
            
            if semester_id:
                semester = Semester.get_by_id(semester_id)
                if semester and 'add_drop_deadline' in semester:
                    # Get the add/drop deadline from the semester document
                    add_drop_deadline = semester.get('add_drop_deadline')
                    
                    # Current date in UTC
                    current_date = datetime.now(timezone.utc)
                    
                    # Log for debugging
                    logger.info(f"Semester data: {semester}")
                    logger.info(f"Add/drop deadline from DB: {add_drop_deadline}")
                    logger.info(f"Current date (UTC): {current_date}")
                    
                    # Compare current date with add/drop deadline to determine if dropping is allowed
                    try:
                        # Add time to the deadline to make it end of day (inclusive)
                        deadline_end_of_day = add_drop_deadline.replace(hour=23, minute=59, second=59)
                        can_drop = current_date <= deadline_end_of_day
                        
                        # Convert to date only for a simpler comparison (backup)
                        current_date_only = current_date.date()
                        deadline_date = add_drop_deadline.date()
                        date_only_comparison = current_date_only <= deadline_date
                        
                        logger.info(f"Date comparison: {current_date} <= {deadline_end_of_day} = {can_drop}")
                        logger.info(f"Date-only comparison: {current_date_only} <= {deadline_date} = {date_only_comparison}")
                        
                        # Use date-only comparison as a fallback
                        if can_drop != date_only_comparison:
                            logger.warning("Date comparisons gave different results, using date-only comparison")
                            can_drop = date_only_comparison
                    except Exception as e:
                        # If there's an error, log it and use a direct string comparison as fallback
                        logger.error(f"Error in date comparison: {str(e)}")
                        # Parse the deadline as string and compare
                        deadline_str = str(add_drop_deadline).split()[0]  # Get just the date part
                        current_str = current_date.strftime('%Y-%m-%d')
                        can_drop = current_str <= deadline_str
                        logger.info(f"String comparison fallback: {current_str} <= {deadline_str} = {can_drop}")
                    
                    logger.info(f"Setting can_drop to {can_drop} based on deadline comparison")
            
            # Log the can_drop value for debugging
            logger.info(f"Course: {course.get('course_name')}, Payment status: {payment_status}, Can drop: {can_drop}")
            
            # Add to enrollment details
            enrollment_details.append({
                'enrollment_id': str(enrollment['_id']),
                'section_id': section_id,
                'course_name': course.get('course_name', 'Unknown'),
                'course_code': course.get('course_code', 'Unknown'),
                'schedule': schedule_display,
                'payment_status': payment_status,
                'can_drop': can_drop
            })
        
        logger.info(f"Prepared {len(enrollment_details)} enrollment details for display")
        return render_template('student/enrollments.html', enrollments=enrollment_details)
        
    except Exception as e:
        logger.error(f"Error in student_view_enrollments: {str(e)}", exc_info=True)
        flash(f"An error occurred while retrieving enrollments: {str(e)}", "error")
        return render_template('student/enrollments.html', enrollments=[])




@app.route('/student_drop_course', methods=['POST'])
def student_drop_course():
    if session.get("user_type") != "student":
        flash("Unauthorized access.", "error")
        return redirect(url_for('student_signin'))
        
    student_id = session.get("user_id")
    enrollment_id = request.form.get('enrollment_id')
    reason = request.form.get('reason', 'Student requested drop')
    
    # Log the received parameters for debugging
    logger.info(f"Drop course - Received parameters: enrollment_id={enrollment_id}, student_id={student_id}")
    
    if not enrollment_id:
        flash("No enrollment specified for drop.", "error")
        return redirect(url_for('student_view_enrollments'))
    
    try:
        # Get the enrollment
        enrollment = Enrollment.get_by_id(enrollment_id)
        
        if not enrollment or str(enrollment['student_id']) != student_id:
            flash("Enrollment not found or unauthorized.", "error")
            return redirect(url_for('student_view_enrollments'))
            
        # Get the section and semester to check add/drop deadline
        section_id = str(enrollment['section_id'])
        section = Section.get_by_id(section_id)
        
        if not section or 'semester_id' not in section:
            flash("Section information not found.", "error")
            return redirect(url_for('student_view_enrollments'))
            
        semester = Semester.get_by_id(str(section['semester_id']))
        
        if not semester or 'add_drop_deadline' not in semester:
            flash("Semester information not found.", "error")
            return redirect(url_for('student_view_enrollments'))
            
        # Get the add/drop deadline from the semester document
        add_drop_deadline = semester.get('add_drop_deadline')
        
        # Current date in UTC
        current_date = datetime.now(timezone.utc)
        
        # Log for debugging
        logger.info(f"Drop course - Semester data: {semester}")
        logger.info(f"Drop course - Add/drop deadline from DB: {add_drop_deadline}")
        logger.info(f"Drop course - Current date (UTC): {current_date}")
        
        # Dynamically compare current date with add/drop deadline to determine if dropping is allowed
        try:
            # Add time to the deadline to make it end of day (inclusive)
            deadline_end_of_day = add_drop_deadline.replace(hour=23, minute=59, second=59)
            can_drop = current_date <= deadline_end_of_day
            
            # Convert to date only for a simpler comparison (backup)
            current_date_only = current_date.date()
            deadline_date = add_drop_deadline.date()
            date_only_comparison = current_date_only <= deadline_date
            
            logger.info(f"Drop course - Date comparison: {current_date} <= {deadline_end_of_day} = {can_drop}")
            logger.info(f"Drop course - Date-only comparison: {current_date_only} <= {deadline_date} = {date_only_comparison}")
            
            # Use date-only comparison as a fallback
            if can_drop != date_only_comparison:
                logger.warning("Drop course - Date comparisons gave different results, using date-only comparison")
                can_drop = date_only_comparison
                
            if not can_drop:
                flash("The add/drop deadline has passed. You can no longer drop this course.", "error")
                return redirect(url_for('student_view_enrollments'))
        except Exception as e:
            # If there's an error, log it and use a direct string comparison as fallback
            logger.error(f"Drop course - Error in date comparison: {str(e)}")
            # Parse the deadline as string and compare
            deadline_str = str(add_drop_deadline).split()[0]  # Get just the date part
            current_str = current_date.strftime('%Y-%m-%d')
            can_drop = current_str <= deadline_str
            logger.info(f"Drop course - String comparison fallback: {current_str} <= {deadline_str} = {can_drop}")
            
            if not can_drop:
                flash("The add/drop deadline has passed. You can no longer drop this course.", "error")
                return redirect(url_for('student_view_enrollments'))
            
        # Check if the course is already paid for
        section_id = str(enrollment['section_id'])
        paid_payment = Payment.collection.find_one({
            'student_id': ObjectId(student_id),
            'courses': ObjectId(section_id),
            'status': 'paid'
        })
        
        # Drop the course
        result = Enrollment.drop_course(enrollment_id, reason)
        
        if result:
            # If course was paid, handle refund logic
            if paid_payment:
                # Calculate refund amount (50% of the course fee)
                course_fee = 100.0  # Fixed amount per course
                refund_amount = course_fee * 0.5  # 50% refund
                
                # Get the semester_id from the section
                section_semester_id = str(section.get('semester_id'))
                
                # Create refund record
                refund_data = {
                    'student_id': ObjectId(student_id),
                    'semester_id': ObjectId(section_semester_id),
                    'payment_id': paid_payment['_id'],
                    'course_id': section.get('course_id'),
                    'section_id': ObjectId(section_id),
                    'amount': refund_amount,
                    'reason': reason,
                    'status': 'processed',
                    'created_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc)
                }
                
                # Update the payment record to refunded status and add refund details
                try:
                    Payment.collection.update_one(
                        {'_id': paid_payment['_id']},
                        {
                            '$set': {
                                'status': 'refunded',
                                'updated_at': datetime.now(timezone.utc),
                                'refund_processed': True,
                                'refund_amount': refund_amount
                            }
                        }
                    )
                    
                    # Create refund record in the refunds collection
                    mongo.db.refunds.insert_one(refund_data)
                    
                    flash("Course dropped successfully. A 50% refund has been processed.", "success")
                except Exception as e:
                    logger.error(f"Error processing refund: {str(e)}")
                    flash(f"Course dropped successfully, but there was an error processing the refund.", "warning")
            else:
                # Remove from unpaid courses
                Payment.collection.update_one(
                    {'student_id': ObjectId(student_id), 'status': 'unpaid'},
                    {'$pull': {'courses': ObjectId(section_id)}}
                )
                flash("Course dropped successfully.", "success")
                
            # Always redirect back to the enrollments page
            return redirect(url_for('student_view_enrollments'))
        else:
            flash("Failed to drop course. Please try again.", "error")
            return redirect(url_for('student_view_enrollments'))
            
    except Exception as e:
        logger.error(f"Course drop failed: {str(e)}")
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('student_view_enrollments'))
