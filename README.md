# DBMS Project — College Management System

A web-based **College Management System** developed as an Advanced Database Management System (ADB/DBMS) project. The application provides role-based functionality for managing students, instructors, courses, semesters, sections, enrollments, payments, fees, and related academic information.

The project is built using **Python, Flask, MongoDB, Flask-PyMongo, and JWT-based authentication** and provides a browser-based interface using HTML templates.

---

## 📌 Project Overview

The College Management System is designed to simplify the management of academic and administrative activities within a college environment.

The system supports multiple user roles and provides functionality for managing academic records, courses, sections, students, instructors, payments, and semester-related information.

### Main User Roles

* **Administrator**
* **Student**
* **Instructor**

Each role has access to functionality appropriate to its responsibilities within the system.

---

## ✨ Features

### 👨‍💼 Administrator

The administrator can manage major academic and administrative operations, including:

* Student management
* Instructor management
* Course management
* Semester management
* Section management
* Enrollment management
* Instructor approval
* Student approval
* Academic information management
* Payment-related management
* Administrative dashboard

### 🎓 Student

Student-related functionality includes:

* Student registration/login
* Student profile management
* Course-related information
* Enrollment-related functionality
* Semester and section information
* Payment-related functionality

### 👨‍🏫 Instructor

Instructor-related functionality includes:

* Instructor registration/login
* Instructor profile
* Course information
* Section information
* Academic management functionality
* Instructor approval workflow

---

## 🛠️ Technologies Used

| Technology         | Purpose                         |
| ------------------ | ------------------------------- |
| Python             | Backend programming language    |
| Flask              | Web application framework       |
| MongoDB            | Database                        |
| Flask-PyMongo      | Flask integration with MongoDB  |
| Flask-JWT-Extended | JWT authentication              |
| Python-dotenv      | Environment variable management |
| HTML5              | Web interface                   |
| Jinja2             | Server-side templating          |
| JavaScript         | Client-side functionality       |
| Git                | Version control                 |
| GitHub             | Source code hosting             |

---

## 🏗️ Project Architecture

The project follows a Flask-based application structure separating application initialization, controllers, models, and templates.

```text
PROJECT(ADB)/
│
├── run.py
│
└── app/
    │
    ├── __init__.py
    ├── main.py
    ├── requirements.txt
    ├── req.txt
    │
    ├── controller/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── course.py
    │   ├── home.py
    │   ├── installment.py
    │   ├── instructor.py
    │   ├── payment.py
    │   ├── section.py
    │   ├── semester.py
    │   └── student.py
    │
    ├── model/
    │   ├── admins.py
    │   ├── courses.py
    │   ├── enrollments.py
    │   ├── fees.py
    │   ├── instructors.py
    │   ├── payments.py
    │   ├── rooms.py
    │   ├── sections.py
    │   ├── semesters.py
    │   └── students.py
    │
    └── templates/
        ├── admin/
        └── ...
```

---

## 🗄️ Database

The application uses **MongoDB** as its database.

The local development database is configured with:

```text
MongoDB
Database: college-sample
```

The application connects to MongoDB using Flask-PyMongo.

### Main Data Areas

The project contains models associated with:

* Administrators
* Students
* Instructors
* Courses
* Semesters
* Sections
* Enrollments
* Payments
* Fees
* Installments
* Rooms

---

## 🔐 Authentication & Security

The application uses **JWT (JSON Web Tokens)** for authentication.

Sensitive configuration values are loaded through environment variables rather than being stored directly in the source code.

The project uses:

```text
Flask-JWT-Extended
python-dotenv
```

### Environment Variables

Create a `.env` file inside the `PROJECT(ADB)` directory:

```env
JWT_SECRET_KEY=your_jwt_secret
FLASK_SECRET_KEY=your_flask_secret
ADMIN_EMAIL=your_admin_email
ADMIN_PASSWORD=your_admin_password
```

> **Important:** Never commit the `.env` file to GitHub. The project `.gitignore` is configured to exclude environment files.

---

## 💻 Prerequisites

Before running the project, install the following:

* Python 3.10+
* MongoDB
* Git
* A code editor such as IntelliJ IDEA or Visual Studio Code

Verify Python:

```bash
python3 --version
```

Verify Git:

```bash
git --version
```

Verify MongoDB is installed and available:

```bash
mongosh --version
```

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/gaddamumeshreddy1481/DBMS-Project.git
```

Move into the project directory:

```bash
cd DBMS-Project
```

---

### 2. Navigate to the application

```bash
cd "PROJECT(ADB)"
```

---

### 3. Create a Python virtual environment

macOS/Linux:

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

Windows:

```bash
python -m venv venv
```

Activate it:

```bash
venv\Scripts\activate
```

---

### 4. Install dependencies

Install the packages listed in `requirements.txt`:

```bash
pip install -r app/requirements.txt
```

If your environment uses the alternate requirements file:

```bash
pip install -r app/req.txt
```

---

## ⚙️ Configuration

Make sure MongoDB is running locally.

The application uses the following MongoDB connection:

```text
mongodb://localhost:27017/college-sample
```

Create the environment file:

```text
PROJECT(ADB)/.env
```

Example:

```env
JWT_SECRET_KEY=your_jwt_secret
FLASK_SECRET_KEY=your_flask_secret
ADMIN_EMAIL=your_admin_email
ADMIN_PASSWORD=your_admin_password
```

Replace the example values with your own local development values.

---

## ▶️ Running the Application

From the `PROJECT(ADB)` directory, activate the virtual environment:

```bash
source venv/bin/activate
```

Then start the Flask application:

```bash
python run.py
```

Alternatively, depending on the Flask configuration, the application can be started using:

```bash
python -m flask run
```

Once the server starts, open the application in your browser at:

```text
http://127.0.0.1:5000
```

or:

```text
http://localhost:5000
```

---

## 📁 Important Files

### `run.py`

Application entry point used to start the Flask application.

### `app/__init__.py`

Initializes the Flask application and configures:

* MongoDB
* JWT
* Environment variables
* Application configuration
* Controllers

### `app/controller/`

Contains the application's route and controller logic.

Examples:

```text
admin.py
student.py
instructor.py
course.py
section.py
semester.py
payment.py
installment.py
```

### `app/model/`

Contains the application's data/model logic.

Examples:

```text
students.py
instructors.py
courses.py
sections.py
semesters.py
enrollments.py
payments.py
fees.py
rooms.py
```

### `app/templates/`

Contains the HTML templates used by the web application.

---

## 🧩 Application Modules

The system is organized around several major modules.

### Student Management

Handles student-related information and operations.

### Instructor Management

Provides instructor registration, approval, and management functionality.

### Course Management

Provides functionality for managing available courses.

### Semester Management

Manages semester-related academic information.

### Section Management

Handles academic sections associated with courses and semesters.

### Enrollment Management

Handles student enrollment information.

### Payment Management

Provides functionality related to student payments and financial records.

### Installment Management

Supports installment-related payment functionality.

### Administration

Provides administrative dashboards and management operations across the system.

---

## 🖼️ Project Documentation

The repository also contains supporting project documentation and visual materials:

* Database Diagram
* Data Dictionary
* Project Description
* Project Presentation and Outputs
* User Interface Screenshots

These resources provide additional information about the database design, project requirements, implementation, and application interface.

---

## 🔄 Git Workflow

After making changes to the project:

```bash
git status
```

Add your changes:

```bash
git add .
```

Commit your changes:

```bash
git commit -m "Describe your changes"
```

Push the changes to GitHub:

```bash
git push
```

To get the latest changes from GitHub:

```bash
git pull
```

---

## 🔒 Files Excluded from Git

The project intentionally excludes development-specific and sensitive files such as:

```text
.env
venv/
.idea/
.DS_Store
__pycache__/
*.pyc
target/
out/
Source codes.zip
```

This keeps the GitHub repository cleaner and prevents local environment files and credentials from being uploaded.

---

## 📊 Project Documentation

The repository includes:

| Resource                                | Description                            |
| --------------------------------------- | -------------------------------------- |
| `Data Dictionary/`                      | Database/data dictionary documentation |
| `Database Diagram.jpg`                  | Database design diagram                |
| `Database description.docx`             | Database documentation                 |
| `Project desription.docx`               | Project description                    |
| `Project Presentation and Outputs.pptx` | Project presentation and outputs       |
| `User Interface screenshots/`           | Application UI screenshots             |
| `PROJECT(ADB)/`                         | Main application source code           |

---

## 👥 Project Information

**Project:** College Management System

**Course:** Advanced Database Management / Database Management System

**Repository:** DBMS-Project

**GitHub:**
https://github.com/gaddamumeshreddy1481/DBMS-Project

---

## 📄 License

This project was developed for academic/educational purposes.

Unless otherwise specified, the source code and project documentation are intended for educational use.
