# FINAL
# +
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema, fields, validates, ValidationError
from datetime import datetime
from sqlalchemy import text

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
db = SQLAlchemy(app)

# Define your models with indexes
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)  # Index on name for fast searching
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)  # Index on email for fast lookup

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, index=True)  # Index on title for fast searching
    due_date = db.Column(db.Date, nullable=False, index=True)  # Index on due_date for faster date filtering
    status = db.Column(db.String(50), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False, index=True)  # Index on student_id for joins

# Create the database tables if they don't exist
with app.app_context():
    db.create_all()

# Define Marshmallow schemas
class StudentSchema(Schema):
    name = fields.Str(required=True)
    email = fields.Email(required=True)

    @validates('email')
    def validate_email(self, email):
        if Student.query.filter_by(email=email).first():
            raise ValidationError("Email must be unique.")

class AssignmentSchema(Schema):
    title = fields.Str(required=True)
    due_date = fields.Date(required=True)
    status = fields.Str(required=True)
    student_id = fields.Int(required=True)

    @validates('due_date')
    def validate_due_date(self, due_date):
        if due_date < datetime.today().date():
            raise ValidationError("Due date must be in the future.")

# Home route
@app.route('/')
def home():
    return render_template('index.html')

# Student routes
@app.route('/students', methods=['POST'])
def create_student():
    schema = StudentSchema()
    try:
        data = schema.load(request.json)
        new_student = Student(name=data['name'], email=data['email'])
        db.session.add(new_student)
        db.session.commit()
        return jsonify({'id': new_student.id, 'name': new_student.name}), 201
    except ValidationError as err:
        db.session.rollback()
        return jsonify({'error': 'Validation Error', 'details': err.messages}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An unexpected error occurred', 'details': str(e)}), 500

@app.route('/students', methods=['GET'])
def get_students():
    students = Student.query.all()
    return jsonify([{'id': student.id, 'name': student.name, 'email': student.email} for student in students])

@app.route('/students/<int:id>', methods=['DELETE'])
def delete_student(id):
    student = Student.query.get(id)
    if student is None:
        return jsonify({'error': 'Student not found'}), 404

    db.session.delete(student)
    db.session.commit()
    return jsonify({'message': 'Student deleted successfully'}), 200

@app.route('/students/<int:id>', methods=['PUT'])
def update_student(id):
    schema = StudentSchema()
    student = Student.query.get(id)
    if student is None:
        return jsonify({'error': 'Student not found'}), 404

    try:
        data = schema.load(request.json)
        student.name = data['name']
        student.email = data['email']
        db.session.commit()
        return jsonify({'message': 'Student updated successfully'}), 200
    except ValidationError as err:
        return jsonify({'error': 'Validation Error', 'details': err.messages}), 400

@app.route('/students/<int:student_id>/assignments', methods=['GET'])
def get_student_assignments(student_id):
    assignments = Assignment.query.filter_by(student_id=student_id).all()
    return jsonify([{
        'id': assignment.id,
        'title': assignment.title,
        'due_date': str(assignment.due_date),
        'status': assignment.status,
        'student_id': assignment.student_id
    } for assignment in assignments])

# Assignment routes
@app.route('/assignments', methods=['POST'])
def create_assignment():
    schema = AssignmentSchema()
    try:
        data = schema.load(request.json)
        new_assignment = Assignment(
            title=data['title'],
            due_date=data['due_date'],
            status=data['status'],
            student_id=data['student_id']
        )
        db.session.add(new_assignment)
        db.session.commit()
        return jsonify({'id': new_assignment.id}), 201
    except ValidationError as err:
        db.session.rollback()
        return jsonify({'error': 'Validation Error', 'details': err.messages}), 400

@app.route('/assignments', methods=['GET'])
def get_assignments():
    assignments = Assignment.query.all()
    return jsonify([{
        'id': assignment.id,
        'title': assignment.title,
        'due_date': str(assignment.due_date),
        'status': assignment.status,
        'student_id': assignment.student_id
    } for assignment in assignments])

@app.route('/assignments/<int:id>', methods=['PUT'])
def update_assignment(id):
    schema = AssignmentSchema()
    assignment = Assignment.query.get(id)
    if assignment is None:
        return jsonify({'error': 'Assignment not found'}), 404

    try:
        data = schema.load(request.json)
        assignment.title = data['title']
        assignment.due_date = data['due_date']
        assignment.status = data['status']
        assignment.student_id = data['student_id']
        db.session.commit()
        return jsonify({'message': 'Assignment updated successfully'}), 200
    except ValidationError as err:
        return jsonify({'error': 'Validation Error', 'details': err.messages}), 400

@app.route('/assignments/<int:id>', methods=['DELETE'])
def delete_assignment(id):
    assignment = Assignment.query.get(id)
    if assignment is None:
        return jsonify({'error': 'Assignment not found'}), 404

    db.session.delete(assignment)
    db.session.commit()
    return jsonify({'message': 'Assignment deleted successfully'}), 200

@app.route('/assignments/all', methods=['GET'])
def view_assignments():
    assignments = Assignment.query.order_by(Assignment.due_date).all()
    return render_template('view_assignments.html', assignments=assignments)

# Route to get students for dropdown
@app.route('/dropdown/students', methods=['GET'])
def dropdown_students():
    students = Student.query.all()
    return jsonify([{'id': student.id, 'name': student.name} for student in students])

@app.route('/report/assignments_per_student', methods=['GET'])
def report_assignments_per_student():
    # Updated query to fetch assignments directly for each student
    query = text("""
    SELECT 
        s.id AS student_id,
        s.name AS student_name,
        a.title AS assignment_title,
        a.due_date AS assignment_due_date
    FROM student s
    LEFT JOIN assignment a ON s.id = a.student_id
    ORDER BY a.due_date
""")

    result = db.session.execute(query).fetchall()

    # Create a dictionary to hold report data with assignments
    report_data = {}
    today = datetime.today().date()  # Get today's date
    
    for row in result:
        student_id = row.student_id
        if student_id not in report_data:
            report_data[student_id] = {
                'student_id': student_id,
                'student_name': row.student_name,
                'assignments': []  # List of assignments
            }

        # Add each assignment to the student's assignment list
        if row.assignment_title:  # Only add assignments if they exist
            due_date = row.assignment_due_date  # Should be of date type
            if isinstance(due_date, str):
                due_date = datetime.strptime(due_date, '%Y-%m-%d').date()  # Convert string to date
            
            report_data[student_id]['assignments'].append({
                'title': row.assignment_title,
                'due_date': due_date
            })

    # Convert report data to a list for rendering
    report_list = list(report_data.values())

    # Calculate days until due for each assignment
    for student in report_list:
        for assignment in student['assignments']:
            days_until_due = (assignment['due_date'] - today).days
            assignment['days_until_due'] = days_until_due  # Add days until due

    return render_template('report_assignments_per_student.html', report_data=report_list, today=today)

# Start the application
if __name__ == '__main__':
    app.run(debug=True)

# -


