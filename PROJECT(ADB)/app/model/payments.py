from app import mongo
from bson import ObjectId, errors
import logging
from datetime import datetime, timezone
from app.model.enrollments import Enrollment
from app.model.students import Student

logger = logging.getLogger(__name__)

class Payment:
    collection = mongo.db.payments
    
    # Payment status constants
    STATUS_UNPAID = 'unpaid'
    STATUS_PAID = 'paid'
    STATUS_PARTIAL = 'partial'
    STATUS_REFUNDED = 'refunded'



    @classmethod
    def update_after_course_drop(cls, student_id, section_id):
        payment = cls.collection.find_one({
            "student_id": ObjectId(student_id),
            "status": "unpaid",
            "courses": ObjectId(section_id)
        })

        if payment:
            cls.collection.update_one(
                {"_id": payment["_id"]},
                {
                    "$pull": {"courses": ObjectId(section_id)},
                    "$set": {"updated_at": datetime.now(timezone.utc)},
                    "$inc": {"total_amount": -100}  # Adjust based on your pricing per course
                }
            )



    @classmethod
    def create_or_update_unpaid(cls, student_id, section_id, course_fee, allow_installments=False, semester_id=None):
        existing = cls.collection.find_one({
            'student_id': ObjectId(student_id),
            'status': 'unpaid',
            'is_installment_plan': {'$ne': True}  # Don't update installment plans
        })

        if existing:
            cls.collection.update_one(
                {'_id': existing['_id']},
                {
                    '$addToSet': {'courses': ObjectId(section_id)},
                    '$inc': {'total_amount': course_fee},
                    '$set': {'updated_at': datetime.utcnow()}
                }
            )
            return cls.collection.find_one({'_id': existing['_id']})
        else:
            new_payment = {
                'student_id': ObjectId(student_id),
                'courses': [ObjectId(section_id)],
                'total_amount': course_fee,
                'status': 'unpaid',
                'is_installment_plan': False,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            if semester_id:
                new_payment['semester_id'] = ObjectId(semester_id)
                
            cls.collection.insert_one(new_payment)
            return new_payment


    @classmethod
    def create_installment_plan(cls, student_id, semester_id, total_amount, courses=None, upfront_amount=0, installment_count=3, payment_details=None, is_full_payment=False):
        """
        Create a payment plan with multiple installments for a semester or process a full payment
        
        Args:
            student_id (str): ID of the student
            semester_id (str): ID of the semester
            total_amount (float): Total fee amount
            courses (list): List of course section IDs
            upfront_amount (float): Amount paid upfront
            installment_count (int): Number of installments (default: 3)
            payment_details (dict): Payment details for automatic first payment
            is_full_payment (bool): Whether this is a full payment (no installments)
            
        Returns:
            dict: Created parent plan with installment IDs
        """
        now = datetime.now(timezone.utc)
        
        # Handle full payment (no installments)
        if is_full_payment:
            # Create a simple payment record
            payment = {
                'student_id': ObjectId(student_id),
                'semester_id': ObjectId(semester_id),
                'total_amount': total_amount,
                'courses': [ObjectId(course_id) for course_id in courses] if courses else [],
                'status': cls.STATUS_PAID,
                'is_installment_plan': False,  # Not an installment plan
                'created_at': now,
                'updated_at': now,
                'payment_date': now,
                'payment_method': 'credit_card',
                'payment_details': payment_details
            }
            
            payment_result = cls.collection.insert_one(payment)
            return cls.collection.find_one({'_id': payment_result.inserted_id})
        
        # If installment count is 1 AND it's a full payment, treat it as a simple payment
        # Otherwise, even with 1 installment, create a proper installment plan if that's what was selected
        if installment_count == 1 and is_full_payment:
            # Create a simple payment record
            payment = {
                'student_id': ObjectId(student_id),
                'semester_id': ObjectId(semester_id),
                'total_amount': total_amount,
                'courses': [ObjectId(course_id) for course_id in courses] if courses else [],
                'status': cls.STATUS_PAID,
                'is_installment_plan': False,  # Not an installment plan
                'created_at': now,
                'updated_at': now,
                'payment_date': now,
                'payment_method': 'credit_card',
                'payment_details': payment_details
            }
            
            payment_result = cls.collection.insert_one(payment)
            return cls.collection.find_one({'_id': payment_result.inserted_id})
        
        # Calculate installment amount after upfront payment
        remaining_amount = max(0, total_amount - upfront_amount)
        installment_amount = round(remaining_amount / installment_count, 2) if installment_count > 0 else 0
        final_installment = remaining_amount - (installment_amount * (installment_count - 1))
        
        # Create parent plan for installment payment
        parent_plan = {
            'student_id': ObjectId(student_id),
            'semester_id': ObjectId(semester_id),
            'total_amount': total_amount,
            'upfront_amount': upfront_amount,
            'remaining_amount': remaining_amount,
            'installment_count': installment_count,
            'courses': [ObjectId(course_id) for course_id in courses] if courses else [],
            'status': cls.STATUS_PARTIAL if installment_count > 1 else cls.STATUS_PAID,  # Set status based on installment count
            'is_installment_plan': True,
            'is_parent_plan': True,
            'installments': [],  # Will store installment IDs
            'created_at': now,
            'updated_at': now,
            'payment_date': now,
            'payment_method': 'credit_card',
            'payment_details': payment_details
        }
        
        parent_result = cls.collection.insert_one(parent_plan)
        parent_plan_id = parent_result.inserted_id
        
        # Create installments with different due dates
        installment_ids = []
        
        for i in range(installment_count):
            # Set due dates 30 days apart
            due_month = ((now.month - 1 + i + 1) % 12) + 1  # Handle month overflow
            due_year = now.year + ((now.month + i) // 12)  # Increment year if needed
            due_date = datetime(due_year, due_month, min(now.day, 28), now.hour, now.minute, now.second, tzinfo=timezone.utc)
            
            # Only the first installment is automatically paid when plan is created
            # For multiple installments, only the first one is paid
            if i == 0 or installment_count == 1:
                status = cls.STATUS_PAID
                payment_date = now
                payment_method = 'credit_card'
            else:
                status = cls.STATUS_UNPAID
                payment_date = None
                payment_method = None
            
            # Calculate installment amount based on installment number
            # First installment should account for upfront payment
            if i == 0 and upfront_amount > 0:
                # First installment is the upfront payment
                amount = upfront_amount
            else:
                # Regular installment amount
                amount = installment_amount if i < installment_count - 1 else final_installment
            
            # Create the installment payment
            installment = {
                'student_id': ObjectId(student_id),
                'semester_id': ObjectId(semester_id),
                'parent_plan_id': parent_plan_id,
                'amount': amount,
                'due_date': due_date,
                'installment_number': i + 1,
                'total_installments': installment_count,
                'status': status,
                'is_installment_plan': True,
                'is_parent_plan': False,
                'payment_method': payment_method,
                'payment_date': payment_date,
                'payment_details': payment_details if i == 0 else None,
                'created_at': now,
                'updated_at': now
            }
            
            result = cls.collection.insert_one(installment)
            installment_ids.append(str(result.inserted_id))
        
        # Update parent plan with installment IDs
        cls.collection.update_one(
            {'_id': parent_plan_id},
            {'$set': {
                'installments': installment_ids,
                'installment_ids': installment_ids
            }}
        )
        
        # Return the parent plan with installment IDs
        parent_plan['_id'] = str(parent_plan_id)
        parent_plan['installment_ids'] = installment_ids
        return parent_plan
    
    @classmethod
    def create(cls, enrollment_id, amount, payment_method):
        """
        Create a new payment record for an enrollment.
        
        Args:
            enrollment_id (str): ID of the enrollment
            amount (float): Payment amount
            payment_method (str): Payment method used
            
        Returns:
            dict: Created payment document
            
        Raises:
            ValueError: If enrollment is invalid or payment amount is incorrect
        """
        try:
            # Validate enrollment
            enrollment = Enrollment.get_by_id(enrollment_id)
            if not enrollment:
                raise ValueError("Invalid enrollment ID")
                
            # Validate payment amount
            if amount <= 0:
                raise ValueError("Payment amount must be greater than zero")
                
            # Create payment
            payment = {
                'enrollment_id': ObjectId(enrollment_id),
                'student_id': enrollment['student_id'],
                'amount': amount,
                'payment_method': payment_method,
                'payment_status': 'pending',  # Possible values: pending, completed, failed, refunded
                'payment_date': datetime.now(),
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            result = cls.collection.insert_one(payment)
            return cls.get_by_id(str(result.inserted_id))
            
        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}")
            raise

    @classmethod
    def get_installments_by_student(cls, student_id):
        """
        Get all installment plans for a student
        
        Args:
            student_id (str): ID of the student
            
        Returns:
            list: List of installment plans with their child installments
        """
        try:
            # Get all parent plans
            parent_plans = list(cls.collection.find({
                'student_id': ObjectId(student_id),
                'is_installment_plan': True,
                'is_parent_plan': True
            }).sort('created_at', -1))
            
            # For each parent plan, get its installments
            for plan in parent_plans:
                plan['_id'] = str(plan['_id'])
                plan['student_id'] = str(plan['student_id'])
                plan['semester_id'] = str(plan['semester_id'])
                
                # Convert course IDs to strings
                if 'courses' in plan:
                    plan['courses'] = [str(course_id) for course_id in plan['courses']]
                
                # Get installments for this plan
                installments = list(cls.collection.find({
                    'parent_plan_id': ObjectId(plan['_id']),
                    'is_installment_plan': True,
                    'is_parent_plan': False
                }).sort('installment_number', 1))
                
                # Convert ObjectIds to strings
                for installment in installments:
                    installment['_id'] = str(installment['_id'])
                    installment['student_id'] = str(installment['student_id'])
                    installment['semester_id'] = str(installment['semester_id'])
                    installment['parent_plan_id'] = str(installment['parent_plan_id'])
                
                plan['installments'] = installments
            
            return parent_plans
            
        except Exception as e:
            logger.error(f"Error getting installments: {str(e)}")
            return []
    
    @classmethod
    def get_installment_by_id(cls, installment_id):
        """
        Get a specific installment by ID
        
        Args:
            installment_id (str): ID of the installment
            
        Returns:
            dict: Installment document
        """
        try:
            installment = cls.collection.find_one({'_id': ObjectId(installment_id)})
            if installment:
                # Convert ObjectIds to strings
                installment['_id'] = str(installment['_id'])
                installment['student_id'] = str(installment['student_id'])
                installment['semester_id'] = str(installment['semester_id'])
                if 'parent_plan_id' in installment:
                    installment['parent_plan_id'] = str(installment['parent_plan_id'])
            return installment
        except Exception as e:
            logger.error(f"Error getting installment: {str(e)}")
            return None
    
    @classmethod
    def pay_installment(cls, installment_id, payment_method, payment_details=None):
        """
        Mark an installment as paid
        
        Args:
            installment_id (str): ID of the installment
            payment_method (str): Method of payment
            payment_details (dict): Additional payment details
            
        Returns:
            dict: Updated installment document
        """
        try:
            # Get the installment
            installment = cls.get_installment_by_id(installment_id)
            if not installment:
                raise ValueError("Installment not found")
                
            if installment['status'] == cls.STATUS_PAID:
                raise ValueError("Installment already paid")
                
            # Update the installment
            now = datetime.now(timezone.utc)
            cls.collection.update_one(
                {'_id': ObjectId(installment_id)},
                {
                    '$set': {
                        'status': cls.STATUS_PAID,
                        'payment_date': now,
                        'payment_method': payment_method,
                        'payment_details': payment_details,
                        'updated_at': now
                    }
                }
            )
            
            # Check if this is part of a parent plan
            if 'parent_plan_id' in installment:
                # Update the parent plan status
                cls._update_parent_plan_status(installment['parent_plan_id'])
                
            return cls.get_installment_by_id(installment_id)
            
        except Exception as e:
            logger.error(f"Error paying installment: {str(e)}")
            raise
    
    @classmethod
    def _update_parent_plan_status(cls, parent_plan_id):
        """
        Update the status of a parent installment plan based on its installments
        
        Args:
            parent_plan_id (str): ID of the parent plan
        """
        try:
            # Get all installments for this plan
            installments = list(cls.collection.find({
                'parent_plan_id': ObjectId(parent_plan_id),
                'is_installment_plan': True,
                'is_parent_plan': False
            }))
            
            # Count paid installments
            total_installments = len(installments)
            paid_installments = sum(1 for inst in installments if inst['status'] == cls.STATUS_PAID)
            
            # Determine new status
            if paid_installments == 0:
                new_status = cls.STATUS_UNPAID
            elif paid_installments < total_installments:
                new_status = cls.STATUS_PARTIAL
            else:
                new_status = cls.STATUS_PAID
                
            # Update the parent plan
            cls.collection.update_one(
                {'_id': ObjectId(parent_plan_id)},
                {
                    '$set': {
                        'status': new_status,
                        'updated_at': datetime.now(timezone.utc)
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating parent plan status: {str(e)}")
    
    @classmethod
    def process_payment(cls, payment_id):
        """
        Process a pending payment.
        
        Args:
            payment_id (str): ID of the payment
            
        Returns:
            dict: Updated payment document
            
        Raises:
            ValueError: If payment is not in pending state
        """
        try:
            payment = cls.get_by_id(payment_id)
            if not payment:
                raise ValueError("Payment not found")
                
            if payment['payment_status'] != 'pending':
                raise ValueError("Payment is not in pending state")
                
            # Simulate payment processing (in a real system, this would interface with a payment gateway)
            payment_status = 'completed'  # In a real system, this would be determined by the payment gateway
            
            # Update payment status
            result = cls.collection.update_one(
                {'_id': ObjectId(payment_id)},
                {
                    '$set': {
                        'payment_status': payment_status,
                        'updated_at': datetime.now()
                    }
                }
            )
            
            if result.modified_count > 0:
                return cls.get_by_id(payment_id)
            
            raise ValueError("Failed to update payment status")
            
        except Exception as e:
            logger.error(f"Error processing payment: {str(e)}")
            raise

    @classmethod
    def refund_payment(cls, payment_id, refund_amount, reason):
        """
        Process a refund for a payment.
        
        Args:
            payment_id (str): ID of the payment
            refund_amount (float): Amount to refund
            reason (str): Reason for refund
            
        Returns:
            dict: Updated payment document
            
        Raises:
            ValueError: If payment is invalid or refund amount is incorrect
        """
        try:
            payment = cls.get_by_id(payment_id)
            if not payment:
                raise ValueError("Payment not found")
                
            if payment['payment_status'] != 'completed':
                raise ValueError("Payment must be completed to process refund")
                
            if refund_amount <= 0 or refund_amount > payment['amount']:
                raise ValueError("Invalid refund amount")
                
            # Update payment status to refunded
            result = cls.collection.update_one(
                {'_id': ObjectId(payment_id)},
                {
                    '$set': {
                        'payment_status': 'refunded',
                        'refund_amount': refund_amount,
                        'refund_reason': reason,
                        'refund_date': datetime.now(),
                        'updated_at': datetime.now()
                    }
                }
            )
            
            if result.modified_count > 0:
                return cls.get_by_id(payment_id)
            
            raise ValueError("Failed to process refund")
            
        except Exception as e:
            logger.error(f"Error processing refund: {str(e)}")
            raise

    @classmethod
    def get_by_id(cls, payment_id):
        """
        Get payment by ID.
        
        Args:
            payment_id (str): ID of the payment
            
        Returns:
            dict: Payment document
        """
        return cls.collection.find_one({'_id': ObjectId(payment_id)})

    @classmethod
    def get_by_student_id(cls, student_id):
        """Get all payments for a student"""
        return list(cls.collection.find({'student_id': ObjectId(student_id)}))
        
    @classmethod
    def get_installments_by_student_semester(cls, student_id, semester_id):
        """Get all installment payments for a student in a specific semester"""
        return list(cls.collection.find({
            'student_id': ObjectId(student_id),
            'semester_id': ObjectId(semester_id),
            'is_installment_plan': True
        }).sort('installment_number', 1))  # Sort by installment number

    @classmethod
    def get_by_enrollment_id(cls, enrollment_id):
        """
        Get payment for an enrollment.
        
        Args:
            enrollment_id (str): ID of the enrollment
            
        Returns:
            dict: Payment document or None if no payment exists
        """
        return cls.collection.find_one({'enrollment_id': ObjectId(enrollment_id)})

    @classmethod
    def get_pending_payments(cls):
        """
        Get all pending payments.
        
        Returns:
            list: List of pending payment documents
        """
        return list(cls.collection.find({'payment_status': 'pending'}))

    @classmethod
    def get_total_revenue(cls, start_date=None, end_date=None):
        """
        Get total revenue for a date range.
        
        Args:
            start_date (datetime, optional): Start date of the range
            end_date (datetime, optional): End date of the range
            
        Returns:
            float: Total revenue
        """
        query = {'payment_status': 'completed'}
        if start_date:
            query['payment_date'] = {'$gte': start_date}
        if end_date:
            query['payment_date'] = {'$lte': end_date}
            
        payments = cls.collection.find(query)
        return sum(payment['amount'] for payment in payments)