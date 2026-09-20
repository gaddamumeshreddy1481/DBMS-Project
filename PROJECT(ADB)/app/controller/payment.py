from flask import render_template, request, redirect, url_for, session, flash
from app import app 
import logging
from datetime import datetime, timedelta, timezone
from bson.objectid import ObjectId 
from flask import jsonify 
from app.model.admins import Admin
from app.model.students import Student
from app.model.instructors import Instructor 
from app.model.semesters import Semester
from app.model.payments import Payment
from app.model.enrollments import Enrollment
from app.model.sections import Section
from app.model.courses import Course



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



@app.route('/student_payments')
def student_payments():
    if session.get("user_type") != "student":
        flash("Unauthorized access.", "error")
        return redirect(url_for('student_signin'))
        
    student_id = session.get("user_id")
    
    # Get all unpaid payments for the student
    unpaid_payments = Payment.collection.find({
        'student_id': ObjectId(student_id),
        'status': 'unpaid',
        'is_installment_plan': {'$ne': True}  # Exclude installment plans
    })
    
    # Get all paid installment plans for the student
    paid_installment_plans = Payment.collection.find({
        'student_id': ObjectId(student_id),
        'status': 'paid',
        'is_installment_plan': True,
        'is_parent_plan': True
    })
    
    # Get all paid payments for the student
    paid_payments = Payment.collection.find({
        'student_id': ObjectId(student_id),
        'status': 'paid'
    })
    
    # Get all refund records for the student
    refund_payments = Payment.collection.find({
        'student_id': ObjectId(student_id),
        'status': 'refunded'
    })
    
    # Get all active enrollments for the student
    active_enrollments = Enrollment.get_active_enrollments(student_id)
    active_section_ids = {str(e['section_id']) for e in active_enrollments}
    
    # Prepare data for display
    unpaid_courses = []
    semester_months = 1
    semester_found = False
    for payment in unpaid_payments:
        for course_id in payment.get('courses', []):
            if str(course_id) not in active_section_ids:
                continue
            section = Section.get_by_id(str(course_id))
            if section:
                course = Course.get_by_id(section.get('course_id'))
                if course:
                    # Get semester info for this section (use the first found)
                    if not semester_found and 'semester_id' in section:
                        semester = Semester.get_by_id(section['semester_id'])
                        if semester and 'start_date' in semester and 'end_date' in semester:
                            start = semester['start_date']
                            end = semester['end_date']
                            if isinstance(start, datetime) and isinstance(end, datetime):
                                # Count months including both start and end months
                                semester_months = (end.year - start.year) * 12 + (end.month - start.month) + 1
                                semester_found = True
                    unpaid_courses.append({
                        'payment_id': str(payment['_id']),
                        'section_id': str(course_id),
                        'course_name': course.get('course_name', 'Unknown'),
                        'course_code': course.get('course_code', 'Unknown'),
                        'amount': 100.0  # Fixed amount per course
                    })
    
    # Prepare paid courses data
    paid_courses = []
    
    # Add courses from regular paid payments
    for payment in paid_payments:
        for course_id in payment.get('courses', []):
            section = Section.get_by_id(str(course_id))
            if section:
                course = Course.get_by_id(section.get('course_id'))
                if course:
                    paid_courses.append({
                        'payment_id': str(payment['_id']),
                        'section_id': str(course_id),
                        'course_name': course.get('course_name', 'Unknown'),
                        'course_code': course.get('course_code', 'Unknown'),
                        'amount': 100.0,  # Fixed amount per course
                        'payment_date': payment.get('updated_at', 'Unknown'),
                        'payment_method': payment.get('payment_method', 'Unknown'),
                        'is_installment': False
                    })
    
    # Add courses from paid installment plans
    for plan in paid_installment_plans:
        for course_id in plan.get('courses', []):
            section = Section.get_by_id(str(course_id))
            if section:
                course = Course.get_by_id(section.get('course_id'))
                if course:
                    paid_courses.append({
                        'payment_id': str(plan['_id']),
                        'section_id': str(course_id),
                        'course_name': course.get('course_name', 'Unknown'),
                        'course_code': course.get('course_code', 'Unknown'),
                        'amount': 100.0,  # Fixed amount per course
                        'payment_date': plan.get('payment_date', plan.get('updated_at', 'Unknown')),
                        'payment_method': plan.get('payment_method', 'Installment Plan'),
                        'is_installment': True,
                        'installment_count': plan.get('installment_count', 0)
                    })
    
    # Format refund records for display
    refund_records = []
    for payment in refund_payments:
        for refund in payment.get('refunds', []):
            section_id = refund.get('section_id')
            section = Section.get_by_id(str(section_id))
            if section:
                course = Course.get_by_id(section.get('course_id'))
                if course:
                    refund_records.append({
                        'course_name': course.get('course_name', 'Unknown'),
                        'course_code': course.get('course_code', 'Unknown'),
                        'original_amount': refund.get('original_amount', 100.0),
                        'refund_amount': refund.get('refund_amount', 0),
                        'refund_date': refund.get('refund_date', payment.get('updated_at', 'Unknown')),
                        'status': 'completed'
                    })
    
    return render_template('student/payments.html', 
                           unpaid_courses=unpaid_courses, 
                           paid_courses=paid_courses,
                           refund_records=refund_records,
                           total_unpaid=sum(course['amount'] for course in unpaid_courses),
                           total_installments=semester_months)









@app.route('/student_make_payment', methods=['POST'])
def student_make_payment():
    if session.get("user_type") != "student":
        flash("Unauthorized access.", "error")
        return redirect(url_for('student_signin'))
        
    student_id = session.get("user_id")
    payment_id = request.form.get('payment_id')
    section_id = request.form.get('section_id')
    
    # If this is a form submission with card details, process the payment
    if request.form.get('card_number'):
        try:
            # Get the payment
            payment = Payment.collection.find_one({
                '_id': ObjectId(payment_id),
                'student_id': ObjectId(student_id),
                'status': 'unpaid'
            })
            
            if not payment:
                flash("Payment not found or already paid.", "error")
                return redirect(url_for('student_payments'))
            
            # In a real system, you would process the payment with a payment gateway here
            # For this demo, we'll just update the payment status
            
            # Collect payment details for record-keeping
            payment_details = {
                'card_number': f"xxxx-xxxx-xxxx-{request.form.get('card_number')[-4:]}",
                'card_holder': request.form.get('card_holder'),
                'payment_date': datetime.now(timezone.utc),
                'billing_address': {
                    'address_line1': request.form.get('address_line1'),
                    'address_line2': request.form.get('address_line2'),
                    'city': request.form.get('city'),
                    'state': request.form.get('state'),
                    'zip_code': request.form.get('zip_code'),
                    'country': request.form.get('country')
                }
            }
            
            # Update payment status to paid
            Payment.collection.update_one(
                {'_id': ObjectId(payment_id)},
                {
                    '$set': {
                        'status': 'paid',
                        'payment_date': datetime.now(timezone.utc),
                        'updated_at': datetime.now(timezone.utc),
                        'payment_details': payment_details
                    }
                }
            )
            
            flash("Payment successful! Your course has been paid for.", "success")
            return redirect(url_for('student_payments'))
            
        except Exception as e:
            logger.error(f"Payment failed: {str(e)}")
            flash(f"An error occurred during payment: {str(e)}", "error")
            return redirect(url_for('student_payments'))
    
    # If this is the initial request, show the payment form
    try:
        # Get the payment and section information for the form
        payment = Payment.collection.find_one({
            '_id': ObjectId(payment_id),
            'student_id': ObjectId(student_id),
            'status': 'unpaid'
        })
        
        if not payment:
            flash("Payment not found or already paid.", "error")
            return redirect(url_for('student_payments'))
        
        # Get course details for the selected section
        section = Section.get_by_id(section_id)
        if not section:
            flash("Section not found.", "error")
            return redirect(url_for('student_payments'))
            
        course = Course.get_by_id(section.get('course_id'))
        if not course:
            flash("Course not found.", "error")
            return redirect(url_for('student_payments'))
        
        # Render the payment form
        return render_template('student/payment_form.html',
                              is_bulk_payment=False,
                              payment_id=payment_id,
                              section_id=section_id,
                              course_name=course.get('course_name', 'Unknown'),
                              course_code=course.get('course_code', 'Unknown'),
                              amount=100.0,
                              form_action=url_for('student_make_payment'))
        
    except Exception as e:
        logger.error(f"Error preparing payment form: {str(e)}")
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('student_payments'))




@app.route('/student_pay_all', methods=['POST'])
def student_pay_all():
    if session.get("user_type") != "student":
        flash("Unauthorized access.", "error")
        return redirect(url_for('student_signin'))
        
    student_id = session.get("user_id")
    
    # If this is a form submission with card details, process the payment
    if request.form.get('card_number'):
        try:
            # Get the unpaid payment
            payment_id = request.form.get('payment_id')
            unpaid_payment = Payment.collection.find_one({
                '_id': ObjectId(payment_id),
                'student_id': ObjectId(student_id),
                'status': 'unpaid'
            })
            if not unpaid_payment:
                flash("No unpaid courses found.", "error")
                return redirect(url_for('student_payments'))
            # Get payment type and form values
            payment_type = request.form.get('payment_type', 'full')
            total_amount = sum(100.0 for _ in unpaid_payment.get('courses', []))
            
            # Set installment parameters based on payment type
            if payment_type == 'full':
                # Full payment - no installments
                num_installments = 1
                upfront_amount = total_amount
                is_installment = False
            else:
                # Installment payment - get values from form
                num_installments = int(request.form.get('installments', 1))
                upfront_amount = float(request.form.get('upfront_amount') or 0)
                is_installment = True  # Always true for installment payment type, even with 1 installment
            
            # Get semester ID for the first course (assuming all courses are in the same semester)
            semester_id = None
            for course_id in unpaid_payment.get('courses', []):
                section = Section.get_by_id(str(course_id))
                if section and 'semester_id' in section:
                    semester_id = str(section['semester_id'])
                    break
            
            if not semester_id:
                flash("Could not determine semester for these courses.", "error")
                return redirect(url_for('student_payments'))
                
            # Get course IDs and create installment plan
            course_ids = [str(course_id) for course_id in unpaid_payment.get('courses', [])]
            
            # Collect payment details for record-keeping
            payment_details = {
                'card_number': f"xxxx-xxxx-xxxx-{request.form.get('card_number')[-4:]}",
                'card_holder': request.form.get('card_holder'),
                'payment_date': datetime.now(timezone.utc),
                'billing_address': {
                    'address_line1': request.form.get('address_line1'),
                    'address_line2': request.form.get('address_line2'),
                    'city': request.form.get('city'),
                    'state': request.form.get('state'),
                    'zip_code': request.form.get('zip_code'),
                    'country': request.form.get('country')
                },
                'installments': num_installments,
                'upfront_amount': upfront_amount
            }
            
            # Create the installment plan
            try:
                # Check if this is a single course payment or bulk payment
                # Determine if this is a bulk payment based on the presence of section_id in the form
                is_bulk_payment = 'section_id' not in request.form
                is_single_course = not is_bulk_payment
                
                if is_single_course:
                    # For single course payment, only include the specified course
                    section_id = request.form.get('section_id')
                    course_ids = [section_id]
                    
                    # Calculate total amount for just this course
                    total_amount = 100.0  # Assuming each course costs $100
                    
                    # Find and update the existing payment record to remove this course
                    Payment.collection.update_one(
                        {'_id': ObjectId(payment_id)},
                        {'$pull': {'courses': ObjectId(section_id)}}
                    )
                    
                    # If no courses left, delete the payment record
                    payment_record = Payment.collection.find_one({'_id': ObjectId(payment_id)})
                    if not payment_record or len(payment_record.get('courses', [])) == 0:
                        Payment.collection.delete_one({'_id': ObjectId(payment_id)})
                else:
                    # For bulk payment, delete the original unpaid payment record
                    Payment.collection.delete_one({'_id': ObjectId(payment_id)})
                
                plan = Payment.create_installment_plan(
                    student_id=student_id,
                    semester_id=semester_id,
                    total_amount=total_amount,
                    courses=course_ids,
                    upfront_amount=upfront_amount,
                    installment_count=num_installments,
                    payment_details=payment_details,
                    is_full_payment=(payment_type == 'full')
                )
                
                # Calculate summary for display
                if payment_type == 'full':
                    summary = "Payment successful! Paid in full."
                else:
                    remaining = max(0, total_amount - upfront_amount)
                    per_installment = remaining / num_installments if num_installments > 0 else 0
                    summary = f"First installment automatically paid. Remaining installments will be due according to the schedule."
            except Exception as e:
                logger.error(f"Error creating installment plan: {str(e)}")
                flash(f"Error creating installment plan: {str(e)}", "error")
                return redirect(url_for('student_payments'))
            
            # If there was an upfront payment, record it
            if upfront_amount > 0:
                # Process the upfront payment
                upfront_payment = {
                    'student_id': ObjectId(student_id),
                    'amount': upfront_amount,
                    'payment_method': 'credit_card',
                    'payment_details': payment_details,
                    'is_upfront_payment': True,
                    'installment_plan_id': ObjectId(plan['_id']),
                    'status': 'paid',
                    'payment_date': datetime.now(timezone.utc),
                    'created_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc)
                }
                Payment.collection.insert_one(upfront_payment)
            
            # Determine the redirect URL based on payment type
            if payment_type == 'full':
                flash("Payment successful! Paid in full.", "success")
                return redirect(url_for('student_payments'))
            else:
                flash(f"Installment plan created successfully! {summary}", "success")
                return redirect(url_for('student_installments'))
            
        except Exception as e:
            logger.error(f"Bulk payment failed: {str(e)}")
            flash(f"An error occurred during payment: {str(e)}", "error")
            return redirect(url_for('student_payments'))
    
    # If this is the initial request, show the payment form
    try:
        # Get all unpaid payments for the student
        unpaid_payment = Payment.collection.find_one({
            'student_id': ObjectId(student_id),
            'status': 'unpaid'
        })
        if not unpaid_payment:
            flash("No unpaid courses found.", "error")
            return redirect(url_for('student_payments'))
        # Calculate total amount
        total_amount = 0
        course_count = 0
        semester_months = 1
        semester_found = False
        for course_id in unpaid_payment.get('courses', []):
            section = Section.get_by_id(str(course_id))
            if section:
                total_amount += 100.0  # Fixed amount per course
                if not semester_found and 'semester_id' in section:
                    semester = Semester.get_by_id(section['semester_id'])
                    if semester and 'start_date' in semester and 'end_date' in semester:
                        start = semester['start_date']
                        end = semester['end_date']
                        if isinstance(start, datetime) and isinstance(end, datetime):
                            semester_months = (end.year - start.year) * 12 + (end.month - start.month) + 1
                            semester_found = True
                course_count += 1
        # Render the payment form
        return render_template('student/payment_form.html',
                              is_bulk_payment=True,
                              payment_id=str(unpaid_payment['_id']),
                              total_amount=total_amount,
                              total_installments=semester_months,
                              form_action=url_for('student_pay_all'))
        
    except Exception as e:
        logger.error(f"Error preparing bulk payment form: {str(e)}")
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('student_payments'))
