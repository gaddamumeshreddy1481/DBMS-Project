from app import mongo
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId, errors
import logging
from datetime import datetime
from app.model.students import Student
from app.model.sections import Section
from app.model.semesters import Semester

logger = logging.getLogger(__name__)

class Enrollment:
    collection = mongo.db.enrollments


    @classmethod
    def get_active_enrollments_by_semester(cls, student_id, semester_id):
        return list(cls.collection.find({
            'student_id': ObjectId(student_id),
            'semester_id': ObjectId(semester_id),
            'status': 'active'
        }))



    @classmethod
    def drop(cls, enrollment_id):
        return cls.drop_course(enrollment_id, reason="Drop by student")


    @classmethod
    def get_students_by_section(cls, section_id):
        return list(cls.collection.find({'section_id': section_id, 'status': 'active'}))

    @classmethod
    def create(cls, student_id, section_id, semester_id):
        try:
            # Check if enrollment window is open
            semester = Semester.get_by_id(semester_id)
            if not semester:
                raise ValueError("Invalid semester ID")
                
            current_date = datetime.now()
            if current_date < semester['enrollment_open_date'] or current_date > semester['enrollment_close_date']:
                raise ValueError("Enrollment window is closed")
                
            # Check if section has available seats
            section = Section.get_by_id(section_id)
            if not section:
                raise ValueError("Invalid section ID")
                
            available_seats = section.get('available_seats', section.get('seat_capacity', 0))
            if available_seats <= 0:
                raise ValueError("Section is full")
                
            # Check for schedule conflicts
            existing_enrollments = cls.collection.find({
                'student_id': ObjectId(student_id),
                'semester_id': ObjectId(semester_id)
            })
            
            for enrollment in existing_enrollments:
                existing_section = Section.get_by_id(str(enrollment['section_id']))
                # check staus of existing enrollment
                if enrollment['status'] == 'dropped':
                    continue
                if cls._has_schedule_conflict(section['schedule'], existing_section['schedule']):
                    raise ValueError("Schedule conflict with existing enrollment")
                    
            # Create enrollment
            enrollment = {
                'student_id': ObjectId(student_id),
                'section_id': ObjectId(section_id),
                'semester_id': ObjectId(semester_id),
                'status': 'active',  # Possible values: active, dropped, waitlisted
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            result = cls.collection.insert_one(enrollment)
            
            # Update section available seats
            Section.decrement_available_seats(section_id)
            
            return cls.get_by_id(str(result.inserted_id))
            
        except Exception as e:
            logger.error(f"Error creating enrollment: {str(e)}")
            raise

    @classmethod
    def drop_course(cls, enrollment_id, reason):
        
        try:
            enrollment = cls.get_by_id(enrollment_id)
            if not enrollment:
                raise ValueError("Enrollment not found")
                
            # Check if drop deadline has passed
            semester = Semester.get_by_id(str(enrollment['semester_id']))
            if not semester:
                raise ValueError("Invalid semester")
                
            current_date = datetime.now()
            if current_date > semester['add_drop_deadline']:
                raise ValueError("Drop deadline has passed")
                
            # Update enrollment status
            result = cls.collection.update_one(
                {'_id': ObjectId(enrollment_id)},
                {
                    '$set': {
                        'status': 'dropped',
                        'drop_reason': reason,
                        'drop_date': datetime.now(),
                        'updated_at': datetime.now()
                    }
                }
            )
            
            if result.modified_count > 0:
                # Update section available seats
                Section.increment_available_seats(str(enrollment['section_id']))
                return cls.get_by_id(enrollment_id)
            
            raise ValueError("Failed to update enrollment status")
            
        except Exception as e:
            logger.error(f"Error dropping course: {str(e)}")
            raise

    @classmethod
    def get_by_id(cls, enrollment_id):
        return cls.collection.find_one({'_id': ObjectId(enrollment_id)})

    @classmethod
    def get_by_student_id(cls, student_id):
        """
        Get all enrollments for a student.
        
        Args:
            student_id (str): ID of the student
            
        Returns:
            list: List of enrollment documents
        """
        return list(cls.collection.find({'student_id': ObjectId(student_id)}))

    @classmethod
    def get_by_section_id(cls, section_id):
        """
        Get all enrollments for a section.
        
        Args:
            section_id (str): ID of the section
            
        Returns:
            list: List of enrollment documents
        """
        try:
            return list(cls.collection.find({'section_id': ObjectId(section_id)}))
        except Exception as e:
            logger.error(f"Error getting enrollments by section ID: {str(e)}")
            return []

    @classmethod
    def get_active_enrollments(cls, student_id):
        """
        Get all active enrollments for a student.
        
        Args:
            student_id (str): ID of the student
            
        Returns:
            list: List of active enrollment documents
        """
        try:
            logger.info(f"Fetching active enrollments for student: {student_id}")
            query = {
                'student_id': ObjectId(student_id),
                'status': 'active'
            }
            logger.info(f"Query: {query}")
            
            # First check if any enrollments exist at all for this student
            all_enrollments = list(cls.collection.find({'student_id': ObjectId(student_id)}))
            logger.info(f"Total enrollments for student (any status): {len(all_enrollments)}")
            if all_enrollments:
                logger.info(f"Sample enrollment: {all_enrollments[0]}")
            
            # Now get active enrollments
            active_enrollments = list(cls.collection.find(query))
            logger.info(f"Active enrollments found: {len(active_enrollments)}")
            return active_enrollments
        except Exception as e:
            logger.error(f"Error getting active enrollments: {str(e)}")
            return []

    @classmethod
    def get_enrollment_count_by_section(cls, section_id):
        """
        Get the count of students enrolled in a specific section.
        
        Args:
            section_id (str): ID of the section
            
        Returns:
            int: Number of students enrolled in the section
        """
        try:
            return cls.collection.count_documents({'section_id': ObjectId(section_id), 'status': 'active'})
        except Exception as e:
            logger.error(f"Error getting enrollment count: {str(e)}")
            return 0
            
    @classmethod
    def get_by_student_and_section(cls, student_id, section_id):
        """
        Check if a student is already enrolled in a specific section.
        
        Args:
            student_id (str): ID of the student
            section_id (str): ID of the section
            
        Returns:
            dict or None: Enrollment document if found, None otherwise
        """
        try:
            return cls.collection.find_one({
                'student_id': ObjectId(student_id),
                'section_id': ObjectId(section_id),
                'status': 'active'
            })
        except Exception as e:
            logger.error(f"Error checking enrollment: {str(e)}")
            return None
            
    @classmethod
    def get_all(cls, query=None):
        """
        Get all enrollments, optionally filtered by query.
        
        Args:
            query (dict, optional): Query filter to apply
            
        Returns:
            list: List of enrollment documents
        """
        if query is None:
            query = {}
        return list(cls.collection.find(query))

    @classmethod
    def update(cls, enrollment_id, update_data):
        """
        Update an enrollment.
        
        Args:
            enrollment_id (str): ID of the enrollment to update
            update_data (dict): Data to update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            update_data['updated_at'] = datetime.now()
            
            result = cls.collection.update_one(
                {'_id': ObjectId(enrollment_id)},
                {'$set': update_data}
            )
            
            # If status is changed to 'dropped', update section available seats
            if update_data.get('status') == 'dropped':
                enrollment = cls.get_by_id(enrollment_id)
                if enrollment and enrollment.get('status') != 'dropped':
                    Section.increment_available_seats(str(enrollment['section_id']))
                    
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating enrollment: {str(e)}")
            return False

    @classmethod
    def get_course_name_by_student_id(cls, student_id):
        """
        Get course names for a student's enrollments.
        
        Args:
            student_id (ObjectId): ID of the student
            
        Returns:
            list: List of course names
        """
        try:
            enrollments = cls.get_by_student_id(str(student_id))
            course_names = []
            
            for enrollment in enrollments:
                if enrollment.get('status') != 'dropped':
                    section = Section.get_by_id(str(enrollment['section_id']))
                    if section:
                        from app.model.courses import Course
                        course = Course.get_by_id(section['course_id'])
                        if course:
                            course_names.append(course['course_name'])
                            
            return course_names
        except Exception as e:
            logger.error(f"Error getting course names for student: {str(e)}")
            return []

    @classmethod
    def _has_schedule_conflict(cls, schedule1, schedule2):
        """
        Check if two schedules (lists of dicts) conflict.
        """
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

    @staticmethod
    def _times_overlap(time1, time2):
        """
        Check if two time periods overlap.
        
        Args:
            time1 (dict): First time period with 'start' and 'end' keys
            time2 (dict): Second time period with 'start' and 'end' keys
            
        Returns:
            bool: True if times overlap, False otherwise
        """
        start1 = datetime.strptime(time1['start'], '%H:%M')
        end1 = datetime.strptime(time1['end'], '%H:%M')
        start2 = datetime.strptime(time2['start'], '%H:%M')
        end2 = datetime.strptime(time2['end'], '%H:%M')
        
        return (start1 <= end2 and end1 >= start2)
