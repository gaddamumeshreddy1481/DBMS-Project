from app import mongo
from bson import ObjectId, errors
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Room:
    collection = mongo.db.rooms
    
    @classmethod
    def create(cls, room_data):
        """
        Create a new room
        
        Args:
            room_data (dict): Room data including room_number, building, capacity
            
        Returns:
            str: ID of the created room
        """
        # Check if room already exists
        existing = cls.collection.find_one({
            "room_number": room_data["room_number"],
            "building": room_data["building"]
        })
        
        if existing:
            raise ValueError("Room already exists")
            
        room_data["created_at"] = datetime.now()
        room_data["updated_at"] = datetime.now()
        
        result = cls.collection.insert_one(room_data)
        return str(result.inserted_id)
    
    @classmethod
    def get_all(cls):
        """Get all rooms"""
        return cls.collection.find().sort("building", 1).sort("room_number", 1)
    
    @classmethod
    def get_by_id(cls, room_id):
        """Get room by ID"""
        try:
            return cls.collection.find_one({"_id": ObjectId(room_id)})
        except errors.InvalidId:
            logger.error(f"Invalid room ID format: {room_id}")
            return None
    
    @classmethod
    def update(cls, room_id, update_data):
        """Update room data"""
        update_data["updated_at"] = datetime.now()
        
        cls.collection.update_one(
            {"_id": ObjectId(room_id)},
            {"$set": update_data}
        )
        
    @classmethod
    def delete(cls, room_id):
        """Delete a room"""
        cls.collection.delete_one({"_id": ObjectId(room_id)})
