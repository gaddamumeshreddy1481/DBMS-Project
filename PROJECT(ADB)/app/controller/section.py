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
from app.model.rooms import Room



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



@app.route('/admin_sections', methods=['GET', 'POST'])
def admin_sections():
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))

    try:
        courses = list(Course.get_all())
        instructors = list(Instructor.get_by_status("approved"))
        semesters = list(Semester.get_all())
        rooms = list(Room.get_all())

        if request.method == 'POST':
            section_id = request.form.get('section_id')
            course_id = request.form.get('course_id')
            instructor_id = request.form.get('instructor_id')
            semester_id = request.form.get('semester_id')
            seat_capacity = int(request.form.get('seat_capacity', 30))
            room_number = request.form.get('room_number')
            
            # Build schedule array from form data
            schedule = []
            for day in request.form.getlist('schedule_days'):
                schedule.append({
                    "day": day,
                    "start_time": request.form.get('start_time'),
                    "end_time": request.form.get('end_time')
                })
            
            # Check if all required fields are provided
            if not all([section_id, course_id, instructor_id, semester_id, schedule]):
                flash("All fields are required. Please select at least one day for the schedule.", "error")
                return redirect(url_for('admin_sections'))
                
            # Create section data
            section_data = {
                "section_id": section_id,
                "course_id": ObjectId(course_id),
                "instructor_id": ObjectId(instructor_id),
                "semester_id": ObjectId(semester_id),
                "schedule": schedule,
                "seat_capacity": seat_capacity,
                "room_number": room_number if room_number else None,
                "created_at": datetime.utcnow(),
                "status": "active"
            }
                
            try:
                # Create the section
                Section.create(section_data)
                flash(f"Section {section_id} created successfully.", "success")
            except ValueError as e:
                flash(str(e), "error")
            except Exception as e:
                logger.error(f"Error creating section: {str(e)}")
                flash("An error occurred while creating the section.", "error")
            return redirect(url_for('admin_sections'))

        # Get all sections for display
        sections = list(Section.get_all_with_details())
        logger.info(f"Retrieved sections: {sections}")
        return render_template(
            "admin/home.html",
            active_tab="sections",
            courses=courses,
            instructors=instructors,
            semesters=semesters,
            sections=sections
        )

    except Exception as e:
        logger.error(f"Error in admin_sections: {str(e)}")
        flash("An error occurred while loading the page.", "error")
        return redirect(url_for('admin_sections'))


@app.route('/admin_update_section/<section_id>', methods=['POST'])
def admin_update_section(section_id):
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))
    
    try:
        # Get selected days from checkboxes
        schedule_days = request.form.getlist('schedule_days')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
        # Format schedule string
        schedule = f"{'/'.join(schedule_days)} {start_time} - {end_time}"
        
        # Prepare update data
        update_data = {
            'course_id': ObjectId(request.form.get('course_id')),
            'instructor_id': ObjectId(request.form.get('instructor_id')),
            'semester_id': ObjectId(request.form.get('semester_id')),
            'schedule': schedule,
            'seat_capacity': int(request.form.get('seat_capacity', 30)),
            'updated_at': datetime.now()
        }
        
        # If room is selected, store room_id
        room_id = request.form.get('room_id')
        if room_id:
            update_data['room_id'] = ObjectId(room_id)
        
        # Update the section
        Section.collection.update_one(
            {"_id": ObjectId(section_id)},
            {"$set": update_data}
        )
        
        flash("Section updated successfully!", "success")
        return redirect(url_for('admin_sections'))
    
    except Exception as e:
        logger.error(f"Error updating section: {str(e)}")
        flash(f"Failed to update section: {str(e)}", "error")
        return redirect(url_for('admin_sections'))


@app.route('/debug_sections')
def debug_sections():
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))
        
    try:
        # Get raw sections
        raw_sections = list(Section.collection.find())
        logger.info(f"Raw sections: {raw_sections}")
        
        # Get sections with details
        sections_with_details = list(Section.get_all_with_details())
        logger.info(f"Sections with details: {sections_with_details}")
        
        return jsonify({
            "raw_sections": raw_sections,
            "sections_with_details": sections_with_details
        })
    except Exception as e:
        logger.error(f"Error in debug_sections: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/admin_edit_section/<section_id>', methods=['GET', 'POST'])
def admin_edit_section(section_id):
    if session.get("user_type") != "admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_signin'))

    section = Section.get_by_id(section_id)
    courses = list(Course.get_all())
    instructors = list(Instructor.get_by_status("approved"))
    semesters = list(Semester.get_all())
    rooms = list(Room.get_all())

    if request.method == 'POST':
        section_id_val = request.form.get('section_id')
        course_id = request.form.get('course_id')
        instructor_id = request.form.get('instructor_id')
        semester_id = request.form.get('semester_id')
        seat_capacity = int(request.form.get('seat_capacity', 30))
        room_number = request.form.get('room_number')
        schedule = []
        for day in request.form.getlist('schedule_days'):
            schedule.append({
                "day": day,
                "start_time": request.form.get('start_time'),
                "end_time": request.form.get('end_time')
            })
        update_data = {
            "course_id": ObjectId(course_id),
            "instructor_id": ObjectId(instructor_id),
            "semester_id": ObjectId(semester_id),
            "schedule": schedule,
            "seat_capacity": seat_capacity,
            "room_number": room_number if room_number else None,
            "updated_at": datetime.utcnow(),
        }
        Section.collection.update_one(
            {"_id": ObjectId(section_id)},
            {"$set": update_data}
        )
        flash("Section updated successfully!", "success")
        return redirect(url_for('admin_sections'))

    return render_template(
        "admin/edit_section.html",
        section=section,
        courses=courses,
        instructors=instructors,
        semesters=semesters,
        rooms=rooms
    )
