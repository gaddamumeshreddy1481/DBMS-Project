from app import mongo
from werkzeug.security import generate_password_hash, check_password_hash

class Admin:
    collection = mongo.db.admins

    @classmethod
    def create(cls, data):
        return cls.collection.insert_one(data)

    @classmethod
    def get_by_email(cls, email):
        return cls.collection.find_one({"email": email})

    @classmethod
    def check_password(cls, admin, password):
        return check_password_hash(admin["password"], password)

    @classmethod
    def exists_by_email(cls, email):
        return cls.collection.find_one({"email": email}) is not None
    