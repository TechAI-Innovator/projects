import mysql.connector
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import csv
import random
import string
from flask import make_response
from random import randint
import os
from dotenv import load_dotenv

password = os.getenv("sql_pw")


# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=password,
        database="school_system"
    )

# Verify user credentials
def verify_user(username, password):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check students
        cursor.execute("SELECT student_id AS user_id, password, CONCAT(first_name, ' ', middle_name, ' ', surname) AS name FROM students WHERE username = %s", (username,))
        student = cursor.fetchone()

        if student and check_password_hash(student['password'], password):
            student['role'] = 'student'
            return student

        # Check staff
        cursor.execute("SELECT staff_id AS user_id, password, CONCAT(first_name, ' ', middle_name, ' ', surname) AS name, is_admin FROM staff WHERE username = %s", (username,))
        staff = cursor.fetchone()

        if staff and check_password_hash(staff['password'], password):
            staff['role'] = 'admin' if staff['is_admin'] else 'staff'
            return staff

    except Exception as e:
        print(f"Error verifying user: {e}")
    finally:
        conn.close()
    
    return None

# Register user
def register_user(form_data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        role = form_data['role']
        registration_code = form_data['registration_code']
        hashed_password = generate_password_hash(form_data['password'])

        if role == 'student':
            # Validate the registration code and get the associated class ID
            cursor.execute(
                "SELECT class_id FROM class_codes WHERE code = %s AND is_used = 0",
                (registration_code,)
            )
            class_info = cursor.fetchone()

            if class_info:
                class_id = class_info[0]

                # Retrieve the role_id for the 'student' role
                cursor.execute("SELECT role_id FROM roles WHERE role_name = %s", (role,))
                role_id_result = cursor.fetchone()

                if role_id_result:
                    role_id = role_id_result[0]

                    # Register the student and mark the code as used
                    cursor.execute(
                        """
                        INSERT INTO students (surname, first_name, middle_name, 
                        username,  password, phone_number, email,
                        date_of_birth, address, class_id, role_id)
                        VALUES (%s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s)
                        """,
                        (form_data['surname'], form_data['firstname'], form_data['middlename'],
                        form_data['username'],  hashed_password, form_data['phonenumber'], form_data['email'],
                        form_data['date'], form_data['address'], class_id, role_id)
                    )
                    student_id = cursor.lastrowid
                    print(student_id)

                    cursor.execute(
                        "UPDATE class_codes SET is_used = 1 WHERE code = %s",
                        (registration_code,)
                    )

                    cursor.execute(
                        "INSERT INTO class_students (class_id, student_id) VALUES (%s, %s)",
                        (class_id, student_id)
                    )
                    conn.commit()
                    return True, "Student registered successfully."
                else:
                    return False, "Role ID for student not found."
            else:
                return False, "Invalid or already used registration code."

        elif role == 'staff':
            cursor.execute(
                "SELECT staff_id FROM staff WHERE verification_code = %s AND code_used = 0",
                (registration_code,)
            )
            verification_result = cursor.fetchone()

            if verification_result:
                staff_id = verification_result[0]

                # Retrieve the role_id for the 'staff' role
                cursor.execute("SELECT role_id FROM roles WHERE role_name = %s", (role,))
                role_id_result = cursor.fetchone()

                if role_id_result:
                    role_id = role_id_result[0]

                    # Update staff details and mark the code as used
                
                    cursor.execute(
                        """
                        UPDATE staff SET 
                        surname = %s, first_name = %s, middle_name = %s,
                        username = %s,  password = %s, phone_number = %s, email = %s,
                        date_of_birth = %s, address = %s, role_id = %s, code_used = 1
                        WHERE staff_id = %s
                        """,
                        (form_data['surname'], form_data['firstname'], form_data['middlename'],
                        form_data['username'],  hashed_password, form_data['phonenumber'], form_data['email'],
                        form_data['date'], form_data['address'], role_id, staff_id)
                    )
                    conn.commit() 
                    return True, "Staff Registered Successfully."
                else:
                    return False, "Role not found for staff.."
            else:
                return False, "Invalid or already used registration code."
        else:
            return False, "Invalid role specified."
    
    except Exception as e:
        print(f'Error registering user: {e}')
        return False, "Registration failed due to an error."
    finally:
        conn.close()

def get_staff_classes(staff_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT c.class_id, c.class_name
            FROM staff_assignments sa
            JOIN classes c ON sa.class_id = c.class_id
            WHERE sa.staff_id = %s
        """, (staff_id,))
        classes = cursor.fetchall()
        seen = []
        for class_item in classes:
            if class_item not in seen:
                seen.append(class_item)
        return seen
    except Exception as e:
        print(f"Error fetching classes: {e}")
        return None
    finally:
        conn.close()

def get_all_classes():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''SELECT class_id AS id, 
                       class_name AS name 
                       FROM classes''')
        classes = cursor.fetchall()
        return classes
    except Exception as e:
        print(f"Error fetching all classes: {e}")
        return None
    finally:
        conn.close()

def get_staff_subjects(staff_id, class_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT s.subject_id, s.subject_name
            FROM staff_assignments sa
            JOIN subjects s ON sa.subject_id = s.subject_id
            WHERE sa.staff_id = %s AND sa.class_id = %s
        """, (staff_id, class_id))
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching subjects: {e}")
        return None
    finally:
        conn.close()


def get_students_by_class_and_subject(class_id, subject_id, staff_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Ensure the staff is assigned to the class and subject
        cursor.execute("""
            SELECT COUNT(*)
            FROM staff_assignments
            WHERE staff_id = %s AND class_id = %s AND subject_id = %s
        """, (staff_id, class_id, subject_id))
        is_assigned = cursor.fetchone()[0] > 0

        if not is_assigned:
            print(f"Staff {staff_id} is not assigned to class {class_id} and subject {subject_id}")
            return None

        # Fetch students in the class for the specific subject
        cursor.execute("""
            SELECT s.student_id, CONCAT(s.surname, ' ', s.first_name, ' ', s.middle_name) AS full_name
            FROM class_students cs
            JOIN students s ON cs.student_id = s.student_id
            WHERE cs.class_id = %s
        """, (class_id,))
        students = cursor.fetchall()
        return students
    except Exception as e:
        print(f"Error fetching students: {e}")
        return None
    finally:
        conn.close()


def save_student_scores(student_id, class_id, subject_id, test1, test2, exam_score, term_id, total_test, total_score, last_term_cum_bf, cumulative_score, pupils_avg):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO scores (student_id, class_id, subject_id, test1, test2, exam_score, term_id, total_test, total_score, last_term_cum_bf, cumulative_score, pupils_avg)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            test1 = COALESCE(VALUES(test1), test1),
            test2 = COALESCE(VALUES(test2), test2),
            exam_score = COALESCE(VALUES(exam_score), exam_score),
            total_test = VALUES(total_test),
            total_score = VALUES(total_score),
            last_term_cum_bf = VALUES(last_term_cum_bf),
            cumulative_score = VALUES(cumulative_score),
            pupils_avg = VALUES(pupils_avg)
        """, (student_id, class_id, subject_id, test1, test2, exam_score, term_id, total_test, total_score, last_term_cum_bf, cumulative_score, pupils_avg))
        conn.commit()

        return True
    except Exception as e:
        print(f"Error saving scores: {e}")
        return False
    finally:
        conn.close()

def get_student_scores(student_id, class_id, subject_id, term_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT test1, test2, exam_score
            FROM scores
            WHERE student_id = %s AND class_id = %s AND subject_id = %s AND term_id = %s
        """, (student_id, class_id, subject_id, term_id))
        return cursor.fetchone()  # Returns a dictionary of scores
    except Exception as e:
        print(f"Error fetching scores for student {student_id}: {e}")
        return None
    finally:
        conn.close()

def get_last_term_cumulative(student_id, class_id, subject_id, current_term_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
         # Fetch the current term and year
        cursor.execute("""
            SELECT term, year 
            FROM terms 
            WHERE term_id = %s
        """, (current_term_id,))
        current_term_info = cursor.fetchone()

        if not current_term_info:
            return 0  # No valid term found

        current_term = current_term_info['term']
        current_year = current_term_info['year']

        # Ignore brought forward for the First Term
        if current_term == 'Term 1':
            return 0

        # Find the previous term by term_id
        cursor.execute("""
            SELECT term_id, term, year 
            FROM terms 
            WHERE term_id < %s
            ORDER BY term_id DESC
            LIMIT 1;
        """, (current_term_id,))
        previous_term_info = cursor.fetchone()

        if not previous_term_info:
            return 0  # No previous term found

        previous_term_id = previous_term_info['term_id']

        # Fetch the cumulative score for the previous term
        cursor.execute("""
            SELECT cumulative_score 
            FROM scores 
            WHERE student_id = %s AND class_id = %s AND subject_id = %s AND term_id = %s
        """, (student_id, class_id, subject_id, previous_term_id))
        result = cursor.fetchone()

        if result and "cumulative_score" in result:
            return float(result["cumulative_score"])
        else:
            return 0

    except Exception as e:
        print(f"Error fetching last term cumulative score: {e}")
        return 0
    finally:
        conn.close()

def get_students_scores(class_id, subject_id, term_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT student_id, pupils_avg
            FROM scores
            WHERE class_id = %s AND subject_id = %s AND term_id = %s
        """, (class_id, subject_id, term_id))
        students_scores = cursor.fetchall()
        students_scores = [
            {'student_id': student['student_id'], 'pupils_avg': float(student['pupils_avg'])}
            for student in students_scores
        ]
        return students_scores
    except Exception as e:
        print(f"Error fetching students' scores: {e}")
        return []
    finally:
        conn.close()

def update_student_position_and_grade(student_id, class_id, subject_id, term_id, class_avg, position, grade):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE scores
            SET class_avg = %s, position = %s, grade = %s
            WHERE student_id = %s AND class_id = %s AND subject_id = %s AND term_id = %s
        """, (class_avg, position, grade, student_id, class_id, subject_id, term_id))
        conn.commit()
    except Exception as e:
        print(f"Error updating position and grade: {e}")
    finally:
        conn.close()

def get_current_and_next_terms():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch the current term
        cursor.execute("SELECT term_id, term, year FROM terms WHERE is_current = True LIMIT 1")
        current_term = cursor.fetchone()

        # Determine the next term
        if current_term:
            term = current_term['term']
            if term == "Term 1":
                next_term = "Term 2"
            elif term == "Term 2":
                next_term = "Term 3"
            elif term == "Term 3":
                next_term = "Term 1"
            else:
                next_term = None
        else:
            term, next_term = None, None

        return {"current_term": term, "next_term": next_term, "term_id": current_term['term_id'], "year": current_term["year"]}
    except Exception as e:
        print(f"Error fetching current and next terms: {e}")
        return {"current_term": None, "next_term": None}
    finally:
        conn.close()

def set_current_term(term, year):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Reset all terms to inactive
        cursor.execute("UPDATE terms SET is_current = FALSE")

        # Set the specified term and year as current
        cursor.execute("""
            INSERT INTO terms (term, year, is_current)
            VALUES (%s, %s, TRUE)
            ON DUPLICATE KEY UPDATE is_current = TRUE, year = %s
        """, (term, year, year))

        conn.commit()
        return True
    except Exception as e:
        print(f"Error setting current term: {e}")
        return False
    finally:
        conn.close()

def get_all_terms():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch all terms
        query = "SELECT term_id AS id, CONCAT(term, ' - ', year) AS term FROM terms ORDER BY year, term"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception as e:
        print(f"Error fetching all terms: {e}")
        return []
    finally:
        conn.close()


def fetch_scores_by_student(student_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Fetch scores for the given student_id
        query = """
            SELECT s.*, t.term, t.year, c.class_name, sub.subject_name
            FROM scores s
            JOIN terms t ON s.term_id = t.term_id
            JOIN classes c ON s.class_id = c.class_id
            JOIN subjects sub ON s.subject_id = sub.subject_id
            WHERE s.student_id = %s
            ORDER BY t.year, t.term
        """
        cursor.execute(query, (student_id,))
        results = cursor.fetchall()
        return results
    except Exception as e:
        print(f"Error fetching scores for student_id {student_id}: {e}")
        return []
    finally:
        conn.close()

def fetch_scores_by_class_and_term(class_id, term_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Fetch scores for the given class, term, and year
        query = """
            SELECT s.*, t.term, t.year, c.class_name, sub.subject_name, CONCAT(st.surname, ' ', st.first_name, ' ', st.middle_name) AS student_name
            FROM scores s
            JOIN terms t ON s.term_id = t.term_id
            JOIN classes c ON s.class_id = c.class_id
            JOIN subjects sub ON s.subject_id = sub.subject_id
            JOIN students st ON s.student_id = st.student_id
            WHERE s.class_id = %s AND t.term_id = %s
            ORDER BY student_name
        """
        cursor.execute(query, (class_id, term_id))
        results = cursor.fetchall()
        return results
    except Exception as e:
        print(f"Error fetching scores for class_id {class_id}, term_id {term_id}: {e}")
        return []
    finally:
        conn.close()














# Login Admin
def login_admin(username, password):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT first_name, surname
            FROM staff
            WHERE username=%s AND password=SHA2(%s, 256) AND is_admin=TRUE
        """, (username, password))
        result = cursor.fetchone()
        return result  # Return user data
    except Exception as e:
        print(f"Error during login: {e}")
        return None
    finally:
        conn.close()




# Check if subject is assigned to a class
def is_subject_assigned_to_class(subject_id, class_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 1 FROM staff_assignments
            WHERE class_id = %s AND subject_id = %s
        """, (class_id, subject_id))
        result = cursor.fetchone()
        return result is not None
    except Exception as e:
        print(f"Error checking subject assignment: {e}")
        return False
    finally:
        conn.close()

def is_class_assigned_to_staff(staff_id, class_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the class is assigned to the staff
        query = """
            SELECT COUNT(*) 
            FROM staff_assignments 
            WHERE staff_id = %s AND class_id = %s
        """
        cursor.execute(query, (staff_id, class_id))
        result = cursor.fetchone()
        return result[0] > 0  # Returns True if the count is greater than 0
    except Exception as e:
        print(f"Error checking if class {class_id} is assigned to staff {staff_id}: {e}")
        return False
    finally:
        conn.close()


# Check if staff already exists
def is_duplicate_staff(surname, first_name, middle_name):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM staff 
            WHERE surname = %s AND first_name = %s AND middle_name = %s
        """, (surname, first_name, middle_name))
        result = cursor.fetchone()
        
        return result[0] > 0  # Returns True if the combination already exists
    except Exception as e:
        print(f"Error checking duplicate staff: {e}")
        return False
    finally:
        conn.close()

# Add Staff
def add_staff(data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if staff already exists
        if is_duplicate_staff(data['surname'], data['first_name'], data['middle_name']):
            print(f"Duplicate staff detected: {data['surname']} {data['first_name']} {data['middle_name']}")
            return False  # Signal a duplicate exists

        # Insert staff
        cursor.execute("""
            INSERT INTO staff (surname, first_name, middle_name, is_admin)
            VALUES (%s, %s, %s, %s)
        """, (data['surname'], data['first_name'], data['middle_name'], data['is_admin']))
        staff_id = cursor.lastrowid

        # Insert staff assignments
        for assignment in data['assignments']:
            cursor.execute("""
                INSERT INTO staff_assignments (staff_id, class_id, subject_id)
                VALUES (%s, %s, %s)
            """, (staff_id, assignment['class_id'], assignment['subject_id']))
        conn.commit()

        return True 
    
    except Exception as e:
        print(f"Error adding staff: {e}") 
        return False
    finally:
        conn.close()




# Get Staff, Class, and Subject Lists
def get_staff_list():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM staff")
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching staff list: {e}")
        return []
    finally:
        conn.close()

def get_class_list():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM classes")
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching class list: {e}")
        return []
    finally:
        conn.close()

def get_subject_list():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM subjects")
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching subject list: {e}")
        return []
    finally:
        conn.close()

# Update Staff Assignments
def update_staff_assignments(data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Remove old assignments
        cursor.execute("DELETE FROM staff_assignments WHERE staff_id=%s", (data['staff_id'],))

        # Add new assignments
        for class_id in data['class_ids']:
            for subject_id in data['subject_ids']:
                cursor.execute("""
                    INSERT INTO staff_assignments (staff_id, class_id, subject_id)
                    VALUES (%s, %s, %s)
                """, (data['staff_id'], class_id, subject_id))
        conn.commit()
    except Exception as e:
        print(f"Error updating assignments: {e}")
    finally:
        conn.close()

# Get Available Classes and Subjects
def get_unassigned_classes_and_subjects():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch classes with available subjects
        cursor.execute("""
            SELECT c.class_id, c.class_name, s.subject_id, s.subject_name
            FROM classes c
            JOIN subjects s ON s.subject_id NOT IN (
                SELECT subject_id FROM staff_assignments WHERE class_id = c.class_id
            )
        """)
        results = cursor.fetchall()

        # Organize classes and their subjects
        classes = {}
        for row in results:
            class_id = row['class_id']
            if class_id not in classes:
                classes[class_id] = {
                    'class_name': row['class_name'],
                    'subjects': []
                }
            classes[class_id]['subjects'].append({
                'subject_id': row['subject_id'],
                'subject_name': row['subject_name']
            })
        return classes
    except Exception as e:
        print(f"Error fetching unassigned classes and subjects: {e}")
        return {}
    finally:
        conn.close()




def get_staff_by_id(staff_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Query to fetch the staff details
        cursor.execute("""
            SELECT staff_id, surname, first_name, middle_name, is_admin
            FROM staff
            WHERE staff_id = %s
        """, (staff_id,))
        return cursor.fetchone()  # Return the staff record as a dictionary
    except Exception as e:
        print(f"Error fetching staff by ID: {e}")
        return None
    finally:
        conn.close()

def get_assigned_classes_and_subjects(staff_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch assigned classes and subjects
        cursor.execute("""
            SELECT c.class_id, c.class_name, s.subject_id, s.subject_name
            FROM staff_assignments sa
            JOIN classes c ON sa.class_id = c.class_id
            JOIN subjects s ON sa.subject_id = s.subject_id
            WHERE sa.staff_id = %s
        """, (staff_id,))
        rows = cursor.fetchall()

        # Organize classes and their subjects
        classes = {}
        for row in rows:
            class_id = row['class_id']
            if class_id not in classes:
                classes[class_id] = {'class_id': class_id, 'class_name': row['class_name'], 'subjects': []}
            classes[class_id]['subjects'].append({'subject_id': row['subject_id'], 'subject_name': row['subject_name']})
        return list(classes.values())
    except Exception as e:
        print(f"Error getting assigned classes and subjects: {e}")
        return None
    finally:
        conn.close()

def delete_staff_classes(staff_id, class_ids):
    placeholders = ','.join(['%s'] * len(class_ids))
    print(placeholders)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
                       DELETE FROM staff_assignments 
                       WHERE staff_id = {'%s'} AND class_id IN ({placeholders})
                    ''', (staff_id, *class_ids))
        conn.commit()
    except Exception as e:
        print(f"Error deleting staff classes: {e}")
        return None
    finally:
        conn.close()

def delete_staff_subjects(staff_id, class_id, subject_ids):
    placeholders = ",".join(["%s"] * len(subject_ids))
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            DELETE FROM staff_assignments
            WHERE staff_id = {'%s'} AND class_id = {'%s'} AND subject_id IN ({placeholders})
        """, (staff_id, class_id, *subject_ids))
        conn.commit()
    except Exception as e:
        print(f"Error deleting staff subjects: {e}")
        return None
    finally:
        conn.close()

def remove_staff(staff_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Remove assignments first
        cursor.execute("DELETE FROM staff_assignments WHERE staff_id = %s", (staff_id,))

        # Remove staff
        cursor.execute("DELETE FROM staff WHERE staff_id = %s", (staff_id,))
        conn.commit()
    except Exception as e:
        print(f"Error removing staff: {e}")
        return None
    finally:
        conn.close()

def assign_subject_to_staff(staff_id, class_id, subject_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert into staff_assignments
        cursor.execute("""
            INSERT INTO staff_assignments (staff_id, class_id, subject_id)
            VALUES (%s, %s, %s)
        """, (staff_id, class_id, subject_id))
        conn.commit()
    except Exception as e:
        print(f"Error assigning subject to staff: {e}")
    finally:
        conn.close()

def assign_subjects_to_classes(assignments):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        for assignment in assignments:
            cursor.execute("""
                INSERT INTO staff_assignments (staff_id, class_id, subject_id)
                VALUES (%s, %s, %s)
            """, (assignment['staff_id'], assignment['class_id'], assignment['subject_id']))

        conn.commit()
        return True
    except Exception as e:
        print(f"Error assigning subjects to classes: {e}")
        return False
    finally:
        conn.close()

def update_admin_status(staff_id, is_admin):

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Update the `is_admin` field
        cursor.execute("""
            UPDATE staff
            SET is_admin = %s
            WHERE staff_id = %s
        """, (is_admin, staff_id))

        conn.commit()
    except Exception as e:
        print(f"Error updating admin status for staff {staff_id}: {e}")
        raise e
    finally:
        conn.close()

    



# Generate Class Codes
def generate_class_codes(batch_size=20):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch all classes
        cursor.execute("SELECT class_id FROM classes")
        classes = cursor.fetchall()
        print(classes)

        # Generate multiple codes for each class
        for class_id, in classes:
            codes = []
            for _ in range(batch_size):
                code = f"{class_id}{randint(1000, 9999)}"  # Unique code with class_id prefix
                codes.append((class_id, code))
                print(codes)
            
            # Insert the codes into a new table `class_codes` or update as needed
            cursor.executemany("""
                INSERT INTO class_codes (class_id, code, is_used)
                VALUES (%s, %s, FALSE)
            """, codes)

        conn.commit()
    except Exception as e:
        print(f"Error generating class codes: {e}")
    finally:
        conn.close()

def fetch_class_codes_for_csv():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.class_name, cc.code
            FROM class_codes cc
            JOIN classes c ON cc.class_id = c.class_id
        """)
        codes = cursor.fetchall()

        # Format data for CSV
        output = [["Class", "Code"]]
        for code in codes:
            output.append([code['class_name'], code['code']])

        return output
    except Exception as e:
        print(f"Error fetching codes for CSV: {e}")
        return []
    finally:
        conn.close()



def generate_staff_verification_codes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch all staff who don't have a verification code yet
        cursor.execute("""
            SELECT staff_id FROM staff
            WHERE verification_code IS NULL
        """)

        for staff_id, in cursor.fetchall():
            code = f"STF{staff_id}{datetime.now().strftime('%H%M%S')}"  # Unique staff code
            cursor.execute("""
                UPDATE staff SET verification_code=%s WHERE staff_id=%s
            """, (code, staff_id))
        conn.commit()
    except Exception as e:
        print(f"Error generating staff verification codes: {e}")
    finally:
        conn.close()

def fetch_staff_codes_for_csv():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT surname, first_name, verification_code FROM staff WHERE verification_code IS NOT NULL")
        codes = cursor.fetchall()

        # Prepare CSV structure
        output = []
        output.append(["Surname", "First Name", "Verification Code"])
        for code in codes:
            output.append([code['surname'], code['first_name'], code['verification_code']])

        return output
    except Exception as e:
        print(f"Error fetching staff codes for CSV: {e}")
        return []
    finally:
        conn.close()

def fetch_class_codes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT c.class_name, cc.code, cc.is_used
            FROM class_codes cc
            JOIN classes c ON cc.class_id = c.class_id
        """)
        class_codes = cursor.fetchall()
        return class_codes
    except Exception as e:
        print(f"Error fetching class codes: {e}")
        return []
    finally:
        conn.close()

def fetch_staff_codes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT surname, first_name, verification_code, code_used
            FROM staff
            WHERE verification_code IS NOT NULL
        """)
        staff_codes = cursor.fetchall()
        return staff_codes
    except Exception as e:
        print(f"Error fetching staff codes: {e}")
        return []
    finally:
        conn.close()