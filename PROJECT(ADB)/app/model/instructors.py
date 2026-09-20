from app import mongo
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId, errors
import logging
from app.model.students import Student

class Instructor:
    collection = mongo.db.instructors

    @classmethod
    def create(cls, data):
        return cls.collection.insert_one(data)
    

    @classmethod
    def get_name_by_id(cls, instructor_id):
        try:
            instructor = cls.collection.find_one({"_id": ObjectId(instructor_id)})
            return instructor["name"] if instructor else None
        except errors.PyMongoError as e:
            return None 
    
        
    @classmethod
    def assign_course(cls, instructor_id, course_id):
        try:
            update_data = {"$unset": {"course_id": ""}} if course_id is None else {"$set": {"course_id": course_id}}
            result = cls.collection.update_one({"_id": instructor_id}, update_data)
            return result.modified_count > 0
        except errors.PyMongoError as e:
            logging.error(f"Error assigning course: {e}")
            return False

    @classmethod
    def get_by_id(cls, instructor_id):
        return cls.collection.find_one({"_id": instructor_id})

    

    @classmethod
    def update_authorization_status(cls, instructor_id, authorization_status, reason=None):
        try:
            update_data = {"$set": {"authorization_status": authorization_status}}
            if reason:
                update_data["$set"]["reason"] = reason
            result = cls.collection.update_one({"_id": ObjectId(instructor_id)}, update_data)
            return result.modified_count > 0
        except errors.PyMongoError as e:
            logging.error(f"Error updating authorization status: {e}")
            return False
            
    @classmethod
    def update_status(cls, instructor_id, status, reason=None):
        try:
            update_data = {"$set": {"status": status}}
            if reason:
                update_data["$set"]["reason"] = reason
            result = cls.collection.update_one({"_id": ObjectId(instructor_id)}, update_data)
            return result.modified_count > 0
        except errors.PyMongoError as e:
            logging.error(f"Error updating status: {e}")
            return False
    

    @classmethod
    def get_by_authorization_status(cls, authorization_status):
        return cls.collection.find({"authorization_status": authorization_status})
        
    @classmethod
    def get_by_status(cls, status):
        return cls.collection.find({"status": status})

    @classmethod
    def get_by_email(cls, email):
        return cls.collection.find_one({"email": email})

    @classmethod
    def check_password(cls, user, password):
        return check_password_hash(user["password"], password)

    @classmethod
    def exists_by_email(cls, email):
        return cls.collection.find_one({"email": email}) is not None

    @classmethod
    def get_user_name_by_id(cls, user_id):
        try:
            user = cls.collection.find_one({"_id": ObjectId(user_id)})  
            return user['name'] if user else None
        except errors.PyMongoError as e: 
            return None

    @classmethod
    def get_user_by_id(cls, user_id):
        try:
            user = cls.collection.find_one({"_id": ObjectId(user_id)})  
            return user
        except errors.PyMongoError as e: 
            return None 
    
    @classmethod
    def find_all(cls):
        return cls.collection.find({})
    


    @classmethod
    def get_students_by_instructor_id(cls, instructor_id):
        instructor = cls.get_by_id(ObjectId(instructor_id))
        if instructor and "course_id" in instructor:
            return Student.get_by_course(instructor["course_id"])
        return []
