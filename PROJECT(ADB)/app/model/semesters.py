from app import mongo
from bson import ObjectId, errors
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Semester:
    collection = mongo.db.semesters

    @classmethod
    def create(cls, semester_name, start_date, end_date, enrollment_open_date, enrollment_close_date, add_drop_deadline):
        try:
            # Convert dates to datetime objects
            try:
                # Try MM/DD/YYYY format first (new format)
                start_date = datetime.strptime(start_date, '%m/%d/%Y')
                end_date = datetime.strptime(end_date, '%m/%d/%Y')
                enrollment_open_date = datetime.strptime(enrollment_open_date, '%m/%d/%Y')
                enrollment_close_date = datetime.strptime(enrollment_close_date, '%m/%d/%Y')
                add_drop_deadline = datetime.strptime(add_drop_deadline, '%m/%d/%Y')
            except ValueError:
                # Fall back to YYYY-MM-DD format (old format)
                try:
                    start_date = datetime.strptime(start_date, '%Y-%m-%d')
                    end_date = datetime.strptime(end_date, '%Y-%m-%d')
                    enrollment_open_date = datetime.strptime(enrollment_open_date, '%Y-%m-%d')
                    enrollment_close_date = datetime.strptime(enrollment_close_date, '%Y-%m-%d')
                    add_drop_deadline = datetime.strptime(add_drop_deadline, '%Y-%m-%d')
                except ValueError as e:
                    raise ValueError(f"Invalid date format. Please use MM/DD/YYYY format (e.g., 05/12/2025): {str(e)}")

            # Validate date order
            if not (enrollment_open_date <= enrollment_close_date <= start_date <= end_date):
                raise ValueError("Dates must follow: enrollment_open <= enrollment_close <= start <= end")
            if add_drop_deadline > end_date:
                raise ValueError("Add/drop deadline must not exceed semester end date")

            # Check if semester_name is unique
            if cls.collection.find_one({'semester_name': semester_name}):
                raise ValueError("Semester name already exists")

            # Check for overlapping date ranges
            overlapping = cls.collection.find_one({
                "$or": [
                    {"start_date": {"$lte": end_date}, "end_date": {"$gte": start_date}}
                ]
            })
            if overlapping:
                raise ValueError("Semester dates overlap with an existing semester")

            # Insert new semester
            semester = {
                'semester_name': semester_name,
                'start_date': start_date,
                'end_date': end_date,
                'enrollment_open_date': enrollment_open_date,
                'enrollment_close_date': enrollment_close_date,
                'add_drop_deadline': add_drop_deadline,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }

            result = cls.collection.insert_one(semester)
            return cls.get_by_id(str(result.inserted_id))

        except Exception as e:
            logger.error(f"Error creating semester: {str(e)}")
            raise

    @classmethod
    def get_by_id(cls, semester_id):
        try:
            return cls.collection.find_one({"_id": ObjectId(semester_id)})
        except errors.InvalidId:
            return None
            
    @classmethod
    def get_previous_semester(cls, current_start_date):
        """Get the most recent semester that ended before the given start date."""
        return cls.collection.find_one(
            {"end_date": {"$lt": current_start_date}},
            sort=[("end_date", -1)]
        )

    @classmethod
    def get_all(cls):
       
        return list(cls.collection.find())

    @classmethod
    def get_current(cls):
     
        current_date = datetime.now()
        return cls.collection.find_one({
            'start_date': {'$lte': current_date},
            'end_date': {'$gte': current_date}
        })

    @classmethod
    def get_upcoming(cls):
        current_date = datetime.now()
        return cls.collection.find_one({
            'start_date': {'$gt': current_date}
        }, sort=[('start_date', 1)])

    @classmethod
    def is_enrollment_open(cls, semester_id):

        semester = cls.get_by_id(semester_id)
        if not semester:
            return False
            
        current_date = datetime.now()
        return (semester['enrollment_open_date'] <= current_date <= semester['enrollment_close_date'])

    @classmethod
    def is_add_drop_period(cls, semester_id):
    
        semester = cls.get_by_id(semester_id)
        if not semester:
            return False
            
        current_date = datetime.now()
        return (semester['start_date'] <= current_date <= semester['add_drop_deadline'])

    @classmethod
    def update(cls, semester_id, data):
        """
        Update a semester's information.
        
        Args:
            semester_id (str): ID of the semester
            data (dict): Fields to update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Validate dates if provided
            if 'start_date' in data:
                data['start_date'] = datetime.strptime(data['start_date'], '%Y-%m-%d')
            if 'end_date' in data:
                data['end_date'] = datetime.strptime(data['end_date'], '%Y-%m-%d')
            if 'enrollment_open_date' in data:
                data['enrollment_open_date'] = datetime.strptime(data['enrollment_open_date'], '%Y-%m-%d')
            if 'enrollment_close_date' in data:
                data['enrollment_close_date'] = datetime.strptime(data['enrollment_close_date'], '%Y-%m-%d')
            if 'add_drop_deadline' in data:
                data['add_drop_deadline'] = datetime.strptime(data['add_drop_deadline'], '%Y-%m-%d')
                
            # Add updated_at timestamp
            data['updated_at'] = datetime.now()
            
            result = cls.collection.update_one(
                {'_id': ObjectId(semester_id)},
                {'$set': data}
            )
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating semester: {str(e)}")
            raise