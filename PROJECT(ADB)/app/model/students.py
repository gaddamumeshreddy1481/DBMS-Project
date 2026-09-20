from app import mongo
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId, errors
import logging

class Student:
    collection = mongo.db.students


    @classmethod
    def get_by_ids(cls, student_ids):
        return cls.collection.find({"_id": {"$in": [ObjectId(id) for id in student_ids]}})

    @classmethod
    def create(cls, data):
        return cls.collection.insert_one(data)
    
    @classmethod
    def get_by_id(cls, student_id):
        return cls.collection.find_one({"_id": ObjectId(student_id)})

    @classmethod
    def get_by_course(cls, course_id):
        return cls.collection.find({"course_id": course_id})


    @classmethod
    def update_status(cls, student_id, status, reason=None):
        try:
            update_data = {"$set": {"status": status}}
            if reason:
                update_data["$set"]["reason"] = reason
            result = cls.collection.update_one({"_id": ObjectId(student_id)}, update_data)
            return result.modified_count > 0
        except errors.PyMongoError as e:
            logging.error(f"Error updating status: {e}")
            return False


    @classmethod
    def get_by_status(cls, status):
        return cls.collection.find({"status": status})
    

    @classmethod
    def get_all(cls):
        return cls.collection.find({})

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
    
    @classmethod
    def find_all(cls):
        return cls.collection.find({})
    

    

    @classmethod
    def assign_course(cls, student_id, course_id):
        try:
            update_data = {"$unset": {"course_id": ""}} if course_id is None else {"$set": {"course_id": course_id}}
            result = cls.collection.update_one({"_id": student_id}, update_data)
            return result.modified_count > 0
        except errors.PyMongoError as e:
            logging.error(f"Error assigning course to student: {e}")
            return False


    @classmethod
    def get_by_course(cls, course_id):
        return cls.collection.find({"course_id": course_id})