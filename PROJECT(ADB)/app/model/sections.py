from app import mongo
from bson import ObjectId, errors
import logging
from datetime import datetime
from app.model.courses import Course
from app.model.instructors import Instructor
from app.model.semesters import Semester

logger = logging.getLogger(__name__)

class Section:
    collection = mongo.db.sections

    @classmethod
    def create(cls, section_data):
        # Enforce unique section_id
        if cls.collection.find_one({"section_id": section_data["section_id"]}):
            raise ValueError("Section ID must be unique.")

        # Check schedule conflicts for each day/time in the schedule
        schedule = section_data.get("schedule", [])
        for schedule_item in schedule:
            conflict = cls.collection.find_one({
                "instructor_id": section_data["instructor_id"],
                "semester_id": section_data["semester_id"],
                "schedule": {
                    "$elemMatch": {
                        "day": schedule_item["day"],
                        "start_time": schedule_item["start_time"],
                        "end_time": schedule_item["end_time"]
                    }
                }
            })
        if conflict:
            raise ValueError("Instructor already has a section with this schedule in this semester.")

        # Ensure required fields for seat capacity and room number
        if "seat_capacity" not in section_data:
            section_data["seat_capacity"] = 30  # Default capacity
        if "room_number" not in section_data:
            section_data["room_number"] = None  # Default to no room assigned

        return cls.collection.insert_one(section_data)

    @classmethod
    def get_duplicate(cls, course_id, instructor_id, semester_id):
        return cls.collection.find_one({
            "course_id": course_id,
            "instructor_id": instructor_id,
            "semester_id": semester_id
        })

    @classmethod
    def get_all_with_details(cls):
        pipeline = [
            {
                "$lookup": {
                    "from": "courses",
                    "localField": "course_id",
                    "foreignField": "_id",
                    "as": "course"
                }
            },
            {"$unwind": "$course"},
            {
                "$lookup": {
                    "from": "instructors",
                    "localField": "instructor_id",
                    "foreignField": "_id",
                    "as": "instructor"
                }
            },
            {"$unwind": "$instructor"},
            {
                "$lookup": {
                    "from": "semesters",
                    "localField": "semester_id",
                    "foreignField": "_id",
                    "as": "semester"
                }
            },
            {"$unwind": "$semester"}
        ]
        return list(cls.collection.aggregate(pipeline))

    @classmethod
    def create_section(cls, data):
        """
        Create a new section with the provided data dictionary.
        
        Args:
            data (dict): Section data including instructor_id, course_id, etc.
            
        Returns:
            bool: True if creation was successful, False otherwise
        """
        try:
            # Add timestamps if not present
            if 'created_at' not in data:
                data['created_at'] = datetime.now()
            if 'updated_at' not in data:
                data['updated_at'] = datetime.now()
                
            # Set default available seats if not specified
            if 'available_seats' not in data and 'max_students' in data:
                data['available_seats'] = data['max_students']
                
            result = cls.collection.insert_one(data)
            return bool(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating section: {str(e)}")
            return False

    @classmethod
    def get_by_id(cls, section_id):
        return cls.collection.find_one({'_id': ObjectId(section_id)})

    @classmethod
    def get_by_course_id(cls, course_id):
        return list(cls.collection.find({'course_id': ObjectId(course_id)}))


    @classmethod
    def get_all(cls, query=None):
        if query is None:
            query = {}
        return list(cls.collection.find(query))

    @classmethod
    def get_by_instructor_id(cls, instructor_id):

        return list(cls.collection.find({'instructor_id': ObjectId(instructor_id)}))

    @classmethod
    def get_by_semester_id(cls, semester_id):
        return list(cls.collection.find({'semester_id': ObjectId(semester_id)}))
            
    @classmethod
    def get_by_instructor_with_course_details(cls, instructor_id):
        """
        Get all sections taught by an instructor with course and semester details.
        """
        try:
            sections = cls.get_by_instructor_id(instructor_id)
            for section in sections:
                # Course details
                if 'course_id' in section:
                    course = Course.get_by_id(section['course_id'])
                    if course:
                        section['course_name'] = course['course_name']
                        section['course_code'] = course.get('course_code', '')

                # Semester details
                if 'semester_id' in section:
                    semester = Semester.get_by_id(section['semester_id'])
                    if semester:
                        section['semester_name'] = semester.get('semester_name', '')

            return sections
        except Exception as e:
            logger.error(f"Error getting sections with details: {str(e)}")
            return []
            
    @classmethod
    def get_all_with_course_details(cls):
        """
        Get all sections with course details.
        
        Returns:
            list: List of section documents with course details
        """
        try:
            sections = list(cls.collection.find())
            for section in sections:
                # Convert ObjectId to string for template use
                section['_id'] = str(section['_id'])
                
                if 'course_id' in section:
                    course = Course.get_by_id(section['course_id'])
                    if course:
                        section['course_name'] = course['course_name']
                        section['course_code'] = course.get('course_code', '')
                        section['credit_hours'] = course.get('credit_hours', 3)
                
                
                # Get instructor name if available
                if 'instructor_id' in section:
                    instructor = Instructor.get_by_id(section['instructor_id'])
                    if instructor:
                        section['instructor_name'] = instructor['name']
            
            return sections
        except Exception as e:
            logger.error(f"Error getting all sections with details: {str(e)}")
            return []

    @classmethod
    def decrement_available_seats(cls, section_id):
        """
        Decrement the available seats in a section by 1.
        
        Args:
            section_id (str): ID of the section
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            section = cls.get_by_id(ObjectId(section_id))
            if not section:
                logger.error(f"Section not found: {section_id}")
                return False
                
            current_seats = section.get('available_seats', section.get('max_students', 30))
            if current_seats <= 0:
                logger.error(f"No available seats in section: {section_id}")
                return False
                
            # Update the available seats
            result = cls.collection.update_one(
                {'_id': ObjectId(section_id)},
                {'$set': {'available_seats': current_seats - 1}}
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error decrementing available seats: {str(e)}")
            return False

    @classmethod
    def increment_available_seats(cls, section_id):

        result = cls.collection.update_one(
            {'_id': ObjectId(section_id)},
            {'$inc': {'available_seats': 1},
             '$set': {'updated_at': datetime.now()}}
        )
        return result.modified_count > 0

    @classmethod
    def _has_schedule_conflict(cls, schedule1, schedule2):
        logger.info(f"Schedule 1: {schedule1}")
        logger.info(f"Schedule 2: {schedule2}")
        
        # Basic fallback: string equality (e.g., both are "MON")
        if isinstance(schedule1, str) and isinstance(schedule2, str):
            return schedule1 == schedule2

        # If one is string and one is dict, treat as no conflict
        if not isinstance(schedule1, dict) or not isinstance(schedule2, dict):
            return False

        # Advanced format: check per day & time overlap
        for day1, times1 in schedule1.items():
                if day1 in schedule2:
                    times2 = schedule2[day1]
                    for time1 in times1:
                        for time2 in times2:
                            if cls._times_overlap(time1, time2):
                                return True
        return False

    @staticmethod
    def _times_overlap(time1, time2):
     
        start1 = datetime.strptime(time1['start'], '%H:%M')
        end1 = datetime.strptime(time1['end'], '%H:%M')
        start2 = datetime.strptime(time2['start'], '%H:%M')
        end2 = datetime.strptime(time2['end'], '%H:%M')
        
        return (start1 <= end2 and end1 >= start2)

    @classmethod
    def get_available_sections(cls, semester_id):
        return list(cls.collection.find({
            'semester_id': ObjectId(semester_id),
            'available_seats': {'$gt': 0}
        }))
        
    @classmethod
    def get_course_name_by_instructor_id(cls, instructor_id):

        try:
            sections = cls.get_by_instructor_id(str(instructor_id))
            course_names = []
            
            for section in sections:
                course = Course.get_by_id(section['course_id'])
                if course:
                    course_names.append(course['course_name'])
                    
            return course_names
        except Exception as e:
            logger.error(f"Error getting course names for instructor: {str(e)}")
            return []
            
    @classmethod
    def delete(cls, section_id):
        """
        Delete a section by ID.
        
        Args:
            section_id (str): ID of the section to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            result = cls.collection.delete_one({'_id': ObjectId(section_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting section: {str(e)}")
            return False