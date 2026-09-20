from app import mongo
from bson.objectid import ObjectId
from datetime import datetime

class Fee:
    @staticmethod
    def create(student_id, semester_id, amount, due_date, description=None):
        """Create a new fee record for a student"""
        fee = {
            "student_id": student_id,
            "semester_id": semester_id,
            "amount": amount,
            "due_date": due_date,
            "description": description,
            "status": "pending",
            "created_at": datetime.now()
        }
        return str(mongo.db.fees.insert_one(fee).inserted_id)
    
    @staticmethod
    def create_installment_plan(student_id, semester_id, total_amount, installment_count=3, description=None):
        """Create a fee payment plan with multiple installments"""
        installment_amount = round(total_amount / installment_count, 2)
        
        # Create installments with different due dates
        now = datetime.now()
        installment_ids = []
        
        for i in range(installment_count):
            # Set due dates 30 days apart
            due_date = datetime(now.year, now.month + i + 1 if now.month + i + 1 <= 12 else (now.month + i + 1) % 12, 
                              min(now.day, 28), now.hour, now.minute, now.second)
            
            # Adjust for year change
            if now.month + i + 1 > 12:
                due_date = due_date.replace(year=now.year + 1)
            
            installment = {
                "student_id": student_id,
                "semester_id": semester_id,
                "amount": installment_amount if i < installment_count - 1 else total_amount - (installment_amount * (installment_count - 1)),
                "due_date": due_date,
                "description": f"Installment {i+1} of {installment_count}: {description}",
                "installment_number": i + 1,
                "total_installments": installment_count,
                "status": "pending",
                "created_at": datetime.now()
            }
            
            installment_id = mongo.db.fees.insert_one(installment).inserted_id
            installment_ids.append(str(installment_id))
        
        return installment_ids
    
    @staticmethod
    def get_by_id(fee_id):
        """Get a fee by ID"""
        return mongo.db.fees.find_one({"_id": ObjectId(fee_id)})
    
    @staticmethod
    def get_by_student_semester(student_id, semester_id):
        """Get all fees for a student in a specific semester"""
        return list(mongo.db.fees.find({"student_id": student_id, "semester_id": semester_id}))
    
    @staticmethod
    def get_by_student(student_id):
        """Get all fees for a student"""
        return list(mongo.db.fees.find({"student_id": student_id}))
    
    @staticmethod
    def update_status(fee_id, status):
        """Update the status of a fee"""
        mongo.db.fees.update_one(
            {"_id": ObjectId(fee_id)},
            {"$set": {"status": status, "updated_at": datetime.now()}}
        )
    
    @staticmethod
    def record_payment(fee_id, amount, payment_method):
        """Record a payment for a fee"""
        payment = {
            "fee_id": fee_id,
            "amount": amount,
            "payment_method": payment_method,
            "payment_date": datetime.now(),
            "status": "completed"
        }
        
        payment_id = mongo.db.payments.insert_one(payment).inserted_id
        
        # Update fee status
        fee = Fee.get_by_id(fee_id)
        if fee and fee["amount"] <= amount:
            Fee.update_status(fee_id, "paid")
        
        return str(payment_id)
