from flask import render_template, request, redirect, url_for, session, flash, jsonify
from app import app
import logging
from datetime import datetime, timezone
from bson.objectid import ObjectId
from app.model.payments import Payment
from app.model.semesters import Semester
from app.model.sections import Section
from app.model.courses import Course
from app.model.students import Student

logger = logging.getLogger(__name__)

@app.route('/student_installments')
def student_installments():
    """View all installment plans for the current student"""
    if session.get("user_type") != "student":
        flash("Unauthorized access.", "error")
        return redirect(url_for('student_signin'))
        
    student_id = session.get("user_id")
    
    # Get all installment plans for the student
    installment_plans = Payment.get_installments_by_student(student_id)
    
    # Prepare data for display - add course names to each plan
    for plan in installment_plans:
        course_details = []
        for course_id in plan.get('courses', []):
            section = Section.get_by_id(course_id)
            if section:
                course = Course.get_by_id(section.get('course_id'))
                if course:
                    course_details.append({
                        'section_id': course_id,
                        'course_name': course.get('course_name', 'Unknown'),
                        'course_code': course.get('course_code', 'Unknown')
                    })
        plan['course_details'] = course_details
        
        # Get semester info
        if 'semester_id' in plan:
            semester = Semester.get_by_id(plan['semester_id'])
            if semester:
                plan['semester_name'] = semester.get('name', 'Unknown Semester')
    
    # Add current date to context for overdue detection
    now = datetime.now(timezone.utc)
    
    # Get student details for payment
    student = Student.get_by_id(student_id)
    
    return render_template('student/installments.html', 
                           installment_plans=installment_plans,
                           student=student,
                           now=now)

@app.route('/student_pay_installment/<installment_id>', methods=['GET', 'POST'])
def student_pay_installment(installment_id):
    """Pay a specific installment"""
    if session.get("user_type") != "student":
        flash("Unauthorized access.", "error")
        return redirect(url_for('student_signin'))
        
    student_id = session.get("user_id")
    
    # Get the installment
    installment = Payment.get_installment_by_id(installment_id)
    if not installment:
        flash("Installment not found.", "error")
        return redirect(url_for('student_installments'))
    
    # Verify this installment belongs to the student
    if str(installment.get('student_id')) != student_id:
        flash("Unauthorized access to this installment.", "error")
        return redirect(url_for('student_installments'))
        
    # Check if installment is already paid
    if installment.get('status') == Payment.STATUS_PAID:
        flash("This installment has already been paid.", "info")
        return redirect(url_for('student_installments'))
    
    # If this is a form submission with card details, process the payment
    if request.method == 'POST' and request.form.get('card_number'):
        try:
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
            
            # Process the payment
            Payment.pay_installment(installment_id, 'credit_card', payment_details)
            
            flash("Installment payment successful!", "success")
            return redirect(url_for('student_installments'))
            
        except Exception as e:
            logger.error(f"Installment payment failed: {str(e)}")
            flash(f"An error occurred during payment: {str(e)}", "error")
            return redirect(url_for('student_installments'))
    
    # Get parent plan to show context
    parent_plan = None
    if 'parent_plan_id' in installment:
        parent_plan = Payment.collection.find_one({'_id': ObjectId(installment['parent_plan_id'])})
        if parent_plan:
            # Get course details
            course_details = []
            for course_id in parent_plan.get('courses', []):
                section = Section.get_by_id(str(course_id))
                if section:
                    course = Course.get_by_id(section.get('course_id'))
                    if course:
                        course_details.append({
                            'section_id': str(course_id),
                            'course_name': course.get('course_name', 'Unknown'),
                            'course_code': course.get('course_code', 'Unknown')
                        })
            parent_plan['course_details'] = course_details
    
    # Render the payment form
    return render_template('student/installment_payment.html',
                          installment=installment,
                          parent_plan=parent_plan,
                          form_action=url_for('student_pay_installment', installment_id=installment_id))


@app.route('/student_quick_pay_installment/<installment_id>', methods=['POST'])
def student_quick_pay_installment(installment_id):
    """Quick pay an installment without entering card details"""
    if session.get("user_type") != "student":
        flash("Unauthorized access.", "error")
        return redirect(url_for('student_signin'))
        
    student_id = session.get("user_id")
    
    # Get the installment
    installment = Payment.get_installment_by_id(installment_id)
    if not installment:
        flash("Installment not found.", "error")
        return redirect(url_for('student_installments'))
    
    # Verify this installment belongs to the student
    if str(installment.get('student_id')) != student_id:
        flash("Unauthorized access to this installment.", "error")
        return redirect(url_for('student_installments'))
        
    # Check if installment is already paid
    if installment.get('status') == Payment.STATUS_PAID:
        flash("This installment has already been paid.", "info")
        return redirect(url_for('student_installments'))
    
    try:
        # Get student details
        student = Student.get_by_id(student_id)
        
        # Create simplified payment details
        payment_details = {
            'quick_payment': True,
            'payment_date': datetime.now(timezone.utc),
            'student_name': student.get('name', 'Unknown Student'),
            'student_email': student.get('email', 'Unknown Email')
        }
        
        # Process the payment
        Payment.pay_installment(installment_id, 'quick_pay', payment_details)
        
        flash("Installment payment successful! Thank you for your payment.", "success")
        return redirect(url_for('student_installments'))
        
    except Exception as e:
        logger.error(f"Quick payment failed: {str(e)}")
        flash(f"An error occurred during payment: {str(e)}", "error")
        return redirect(url_for('student_installments'))
