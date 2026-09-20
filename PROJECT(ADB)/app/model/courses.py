from app import mongo
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from pymongo import errors
import logging


class Course:
    collection = mongo.db.courses
    logger = logging.getLogger(__name__)

    @classmethod
    def get_by_id(cls, course_id):
        """
        Get a course by its ID.
        
        Args:
            course_id (str): ID of the course
            
        Returns:
            dict: Course document or None if not found
        """
        try:
            cls.logger.info(f"Looking up course with ID: {course_id}")
            if not course_id:
                cls.logger.warning("Course ID is empty or None")
                return None
                
            # Check if the course_id is a valid ObjectId
            if not ObjectId.is_valid(course_id):
                cls.logger.warning(f"Invalid ObjectId format for course_id: {course_id}")
                return None
                
            course = cls.collection.find_one({'_id': ObjectId(course_id)})
            if course:
                cls.logger.info(f"Found course: {course}")
            else:
                cls.logger.warning(f"No course found with ID: {course_id}")
            return course
        except Exception as e:
            cls.logger.error(f"Error getting course by ID: {str(e)}")
            return None

    @classmethod
    def create(cls, data):
        return cls.collection.insert_one(data)


    @classmethod
    def get_all(cls):
        return cls.collection.find()
    

    @classmethod
    def get_course_name_by_id(cls, course_id):
        course = cls.collection.find_one({"_id": course_id})
        print(course)
        return course['course_name'] if course else None

    @classmethod
    def assign_course(cls, student_id, course_id):
        try:
            update_data = {"$unset": {"course_id": ""}} if course_id is None else {"$set": {"course_id": course_id}}
            result = cls.collection.update_one({"_id": student_id}, update_data)
            return result.modified_count > 0
        except errors.PyMongoError as e:
            logging.error(f"Error assigning course to student: {e}")
            return False
