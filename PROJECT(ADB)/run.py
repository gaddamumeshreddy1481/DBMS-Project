from app import app
from app.controller import admin, instructor, student, home, course, semester, section, payment
from app.controller import installment
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)