from flask import Flask, session, render_template, request, Response, redirect, url_for, jsonify, flash
# Learn from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from datetime import datetime
from engine import (
    verify_user,
    register_user,
    login_admin,
    add_staff,
    get_staff_list,
    get_class_list,
    get_subject_list,
    update_staff_assignments,
    get_staff_by_id,
    remove_staff,
    delete_staff_subjects,
    delete_staff_classes,
    get_assigned_classes_and_subjects,
    generate_class_codes,
    fetch_class_codes_for_csv,
    fetch_staff_codes_for_csv,
    generate_staff_verification_codes,
    get_unassigned_classes_and_subjects,
    assign_subjects_to_classes,
    assign_subject_to_staff,
    update_admin_status,
    is_subject_assigned_to_class,
    fetch_class_codes,
    fetch_staff_codes,
    get_staff_classes,
    get_staff_subjects,
    get_students_by_class_and_subject,
    save_student_scores,
    set_current_term,
    get_current_and_next_terms,
    get_current_and_next_terms,
    get_student_scores,
    get_last_term_cumulative,
    update_student_position_and_grade,
    get_students_scores,
    fetch_scores_by_student,
    fetch_scores_by_class_and_term,
    get_all_classes,
    get_all_terms,
    is_class_assigned_to_staff
)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route('/')
def index():
    # If the user is already logged in, redirect to their dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    # Otherwise, show the login page
    return redirect(url_for('login'))

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = verify_user(username, password)

        if user:
            session['user_id'] = user['user_id']
            session['role'] = user['role']
            session['user_name'] = user['name']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login_page.html')

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    return render_template('logout.html')

# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        form_data = request.form
        success, message = register_user(form_data)
        
        if success:
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
            return redirect('register')

    return render_template('registration_page.html')

# Dashboard Route
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_role = session.get('role')
    user_name = session.get('user_name')

    return render_template('Dashboard.html',
                           user_role=user_role,
                           user_name=user_name,
                           current_page='dashboard'
                           )

# Score entry route
@app.route('/score-entry', methods=['GET'])
def score_entry():
    staff_id = session.get('user_id')
    user_role = session.get('role')
    user_name = session.get('user_name')

    args = request.args.to_dict()
    
    current_term_year = get_current_and_next_terms()
    term_id = current_term_year['term_id']
    current_term = current_term_year['current_term']
    current_year = current_term_year['year']

    if 'class_id' in args:
        new_class_id = int(args.get('class_id'))
        current_class_id = session.get('class_id')

        # Update session with the new class_id
        session['class_id'] = new_class_id

        # Reset subject_id if class_id has changed
        if current_class_id != new_class_id:
            session.pop('subject_id', None)  # Remove the previous subject_id from session
            args['subject_id'] = None       # Reassign None to subject_id in args

    # Only process subject_id if it exists in args and is not None
    if 'subject_id' in args and args['subject_id'] is not None:
        session['subject_id'] = int(args['subject_id'])

    class_id = session.get('class_id')
    subject_id = session.get('subject_id')

    # Fetch classes for the staff
    classes = get_staff_classes(staff_id)

    # Fetch subjects for the selected class
    subjects = get_staff_subjects(staff_id, class_id) if class_id else []

    # Fetch students and their scores
    students = []
    if class_id and subject_id:
        student_list = get_students_by_class_and_subject(class_id, subject_id, staff_id)
        for student in student_list:
            student_id = student[0]
            full_name = student[1]
            scores = get_student_scores(student_id, class_id, subject_id, term_id)
            # Include student ID, name, and scores in the list
            students.append({
                "student_id": student_id,
                "full_name": full_name,
                "test1": scores["test1"] if scores else None,
                "test2": scores["test2"] if scores else None,
                "exam_score": scores["exam_score"] if scores else None,
            })


    return render_template('score_entry.html',
                           user_role=user_role,
                           user_name=user_name,
                           classes=classes,
                           subjects=subjects,
                           students=students,
                           selected_class_id=class_id,
                           selected_subject_id=subject_id,
                           current_term=current_term,
                           current_year=current_year,
                           current_page='score-entry'
                           )


@app.route('/reset-filters')
def reset_filters():
    session.pop('staff_if', None)
    session.pop('class_id', None)
    session.pop('subject_id', None)
    return redirect('/score-entry')

    
@app.route('/submit-scores', methods=['POST'])
def submit_scores():
    form_data = request.form.to_dict(flat=True) # Get all scores submitted
    scores = {}
    staff_id = session.get('user_id')

    current_term_year = get_current_and_next_terms()
    term_id = current_term_year['term_id']
    term_number = {'Term 1': 1, 'Term 2': 2, 'Term 3': 3}[current_term_year['current_term']]

    # Class and subject IDs from session
    class_id = session.get('class_id')
    subject_id = session.get('subject_id')

    if not staff_id or not class_id or not subject_id:
        flash("Invalid session data. Please select a class and subject.", "error")
        return redirect('/score-entry')

    # Process each student's scores
    for key, value in form_data.items():
        try:
            if key.startswith('scores['):
                parts = key.split("][")
                student_id = parts[0][7:]  # Extract '1' from scores[1]
                score_type = parts[1][:-1]  # Extract 'test1' from [test1]

                # Initialize scores dictionary for the student if not already there
                if student_id not in scores:
                    scores[student_id] = {
                        "test1": None,
                        "test2": None,
                        "exam_score": None
                    }

                # Assign values to the correct score type
                if score_type in scores[student_id]:
                    scores[student_id][score_type] = float(value) if value else None
                    
        except Exception as e:
            flash(f"Error saving scores for student ID {key}: {e}", "error")
            continue

    # Save scores to database
    for student_id, score_data in scores.items():
        try:
            total_test = (score_data["test1"] or 0) + (score_data["test2"] or 0)
            total_score = total_test + (score_data["exam_score"] or 0)

            # Get last term's cumulative score
            last_term_cum_bf = get_last_term_cumulative(student_id, class_id, subject_id, term_id)

            # Calculate cumulative score
            cumulative_score = total_score + (last_term_cum_bf)
            # Calculate pupils average
            pupils_avg = round(cumulative_score / term_number, 2)
            
            save_student_scores(
                student_id=student_id,
                class_id=class_id,
                subject_id=subject_id,
                test1=score_data['test1'],
                test2=score_data['test2'],
                exam_score=score_data['exam_score'],
                term_id=term_id,
                total_test=total_test,
                total_score=total_score,
                last_term_cum_bf=last_term_cum_bf,
                cumulative_score=cumulative_score,
                pupils_avg=pupils_avg
            )

        except Exception as e:
            flash(f"Error saving scores for student ID {student_id}: {e}", "error")
            continue
    
    # Fetch all students in the class for the subject
    students_scores = get_students_scores(class_id, subject_id, term_id)

    # Calculate class average
    pupils_avgs = [student["pupils_avg"] for student in students_scores]
    class_avg = sum(pupils_avgs) / len(pupils_avgs) if pupils_avgs else 0

    # Assign positions
    students_scores.sort(key=lambda x: x["pupils_avg"], reverse=True)
    position = 1
    last_avg = None
    tie_count = 0

    for student in students_scores:
        if last_avg is None or student["pupils_avg"] < last_avg:
            position += tie_count
            tie_count = 0

        student["position"] = position
        last_avg = student["pupils_avg"]
        tie_count += 1

    # Save positions and grades
    for student in students_scores:
        pupils_avg = student["pupils_avg"]
        grade = (
            "A" if pupils_avg >= 90 else
            "B" if pupils_avg >= 80 else
            "C" if pupils_avg >= 70 else
            "D" if pupils_avg >= 60 else "F"
        )

        update_student_position_and_grade(
            student_id=student["student_id"],
            class_id=class_id,
            subject_id=subject_id,
            term_id=term_id,
            class_avg=class_avg,
            position=student["position"],
            grade=grade,
        )

    flash("Scores submitted successfully.", "success")
    return redirect('/score-entry')


@app.route('/set-term', methods=['POST'])
def set_term():
    term = request.form.get('term')
    year = datetime.now().year

    if set_current_term(term, year):
        flash("Current term updated successfully.", "success")
    else:
        flash("Error updating current term.", "error")

    return redirect('/admin-dashboard')

@app.route('/student-report', methods=['GET'])
def student_report():
    user_id = session.get('user_id')
    user_role = session.get('role')
    user_name = session.get('user_name')


    if user_role == 'student':
        scores = fetch_scores_by_student(user_id)
        return render_template('student_report.html',
                               scores=scores,
                               user_role=user_role,
                               user_name=user_name,
                               current_page='student-report'
                               )
    else:
        flash("Unauthorized access to student report.", "error")
        return redirect('/dashboard')

@app.route('/class-report', methods=['GET', 'POST'])
def class_report():
    user_id = session.get('user_id')
    user_role = session.get('role')
    user_name = session.get('user_name')


    if user_role not in ['staff', 'admin']:
        flash("Unauthorized access to class report.", "error")
        return redirect('/dashboard')

    classes = get_staff_classes(user_id) if user_role == 'staff' else get_all_classes()
    terms = get_all_terms()
    scores = []

    # Initialize variables to prevent reference errors
    class_id = None
    term_id = None

    if request.method == 'POST':
        class_id = request.form.get('class_id', type=int)
        term_id = request.form.get('term_id', type=int)

        if user_role == 'staff' and not is_class_assigned_to_staff(user_id, class_id):
            flash("You are not authorized to view this class.", "error")
            return redirect('/class-report')

        scores = fetch_scores_by_class_and_term(class_id, term_id)

    return render_template('class_report.html',
                           classes=classes,
                           terms=terms,
                           scores=scores,
                           selected_class_id = class_id,
                           selected_term_id = term_id,
                           user_role=user_role,
                           user_name=user_name,
                           current_page='class-report'
                           )

# Update Profile route
@app.route('/update-profile')
def update_profile():

    '''
    Define what this does late
    '''

    return render_template('profile.html')

# Contact Route
@app.route('/contact')
def contact():
    return render_template('contact.html')

# Help and Support Route
@app.route('/help')
def help():
    return render_template('help.html')

# Admin Dashboard
@app.route('/admin-dashboard')
def admin_dashboard():
    # Assuming you store the logged-in user's info in the session
    user_role = session.get('role')
    user_name = session.get('user_name')
    print(f"User Name in Session: {session.get('user_name')}")
    if request.method == 'GET':
        term_data = get_current_and_next_terms()
        current_term = term_data['current_term']
        next_term = term_data['next_term']
        year = datetime.now().year

    if request.method == 'POST':
        selected_term = request.form.get('term')
        if selected_term == next_term:
            if set_current_term(selected_term, year):
                flash("Term updated successfully.", "success")
            else:
                flash("Error updating term.", "error")
        else:
            flash("Invalid term selection.", "error")
        return redirect('/admin-dashboard')

    return render_template('admin_dashboard.html',
                           user_name=user_name,
                           user_role=user_role,
                           current_term=current_term,
                           next_term=next_term,
                           current_page='admin-dashboard'
                           )


# Add Staff
@app.route('/add-staff', methods=['GET', 'POST'])
def add_staff_route():
    if request.method == 'POST':
        try:
            data = {
                'surname': request.form['surname'],
                'first_name': request.form['first_name'],
                'middle_name': request.form.get('middle_name'),
                'is_admin': 'is_admin' in request.form,
                'assignments': []
            }

            # Collect assignments from form data
            for key, subject_ids in request.form.lists():
                if key.startswith('subject_assignment'):
                    class_id = key.split('[')[1].split(']')[0]
                    
                    if class_id.isdigit():
                        for subject_id in subject_ids:
                            if subject_id.isdigit():
                                data['assignments'].append({
                                    'class_id': int(class_id),
                                    'subject_id': int(subject_id)
                                })

            if not data['assignments']:
                flash('At least one class and subject must be selected.', 'error')
                return redirect(url_for('add_staff_route'))

            # Add staff
            if add_staff(data):
                flash('Staff added successfully!', 'success')
            else:
                flash('Staff could not be added. Possible duplicate or error.', 'error')

            return redirect(url_for('dashboard'))

        except Exception as e:
            flash('An unexpected error occurred.', 'error')
            return redirect(url_for('add_staff_route'))

    # Fetch class and subject data for the form
    try:
        class_list = get_class_list()
        subject_list = get_subject_list()
        available_subjects = [
            {
                'class': cls,
                'subjects': [
                    subject for subject in subject_list
                    if not is_subject_assigned_to_class(subject['subject_id'], cls['class_id'])
                ]
            }
            for cls in class_list
        ]

        return render_template('add_staff.html', available_subjects=available_subjects)
    except Exception as e:
        flash('Unable to load data for adding staff.', 'error')
        return redirect(url_for('dashboard'))



# Manage Staff
@app.route('/manage-staff', methods=['GET', 'POST'])
def manage_staff():
    staff_list = get_staff_list()  # Fetch the staff list
    class_list = get_class_list()  # Fetch the class list
    subject_list = get_subject_list()  # Fetch the subject list
    return render_template('manage_staff.html', 
                           staff_list=staff_list, 
                           class_list=class_list, 
                           subject_list=subject_list)


@app.route('/fetch-staff-assignments', methods=['POST'])
def fetch_staff_assignments():
    staff_id = request.form['staff_id']
    selected_staff = get_staff_by_id(staff_id)
    assigned_classes = get_assigned_classes_and_subjects(staff_id)
    unassigned_classes = get_unassigned_classes_and_subjects()
    unassigned_subjects = []  # Filter subjects for already assigned classes

    unassigned_classes = dict(
        sorted(unassigned_classes.items(), key=lambda item: item[1]["class_name"])
    )

    # Identify unassigned subjects within assigned classes
    for assigned_class in assigned_classes:
        available_subjects = [
            subject for subject in get_subject_list()
            if not is_subject_assigned_to_class(subject['subject_id'], assigned_class['class_id'])
        ]
        unassigned_subjects.append({
            'class_id': assigned_class['class_id'],
            'class_name': assigned_class['class_name'],
            'subjects': available_subjects
        })

    return render_template(
        'manage_staff.html',
        staff_list=get_staff_list(),
        selected_staff=selected_staff,
        assigned_classes=assigned_classes,
        unassigned_classes=unassigned_classes,
        unassigned_subjects=unassigned_subjects
    )


@app.route('/delete-classes', methods=['POST'])
def delete_classes():
    staff_id = request.form['staff_id']
    class_ids = [int(sid) for sid in request.form.getlist('class_ids[]')]
    delete_staff_classes(staff_id, class_ids)
    flash("Selected classes deleted successfully.", "success")
    return redirect(url_for('manage_staff'))

@app.route('/delete-subjects', methods=['POST'])
def delete_subjects():
    staff_id = request.form['staff_id']
    class_id = request.form['class_id']
    subject_ids = [int(sid) for sid in request.form.getlist('subject_ids[]')]
    delete_staff_subjects(staff_id, class_id, subject_ids)
    flash("Selected subjects deleted successfully.", "success")
    return redirect(url_for('manage_staff'))

@app.route('/delete-staff', methods=['POST'])
def delete_staff():
    staff_id = request.form['staff_id']
    remove_staff(staff_id)
    flash("Staff deleted successfully.", "success")
    return redirect(url_for('manage_staff'))

@app.route('/add-classes-and-subjects', methods=['POST'])
def add_classes_and_subjects():
    staff_id = request.form['staff_id']
    assignments = {}
    for key, values in request.form.lists():
        if key.startswith("assignments["):
            class_id = int(key.split("[")[1].split("]")[0])
            assignments[class_id] = values

    # Format assignments into a list of dictionaries
    formatted_assignments = [
        {'staff_id': staff_id, 'class_id': int(class_id), 'subject_id': int(subject_id)}
        for class_id, subject_ids in assignments.items()
        for subject_id in subject_ids
    ]

    if formatted_assignments:
        success = assign_subjects_to_classes(formatted_assignments)
        if success:
            flash("Subjects successfully assigned to classes!", "success")
        else:
            flash("Error occurred while assigning subjects.", "error")
    else:
        flash("No classes or subjects selected.", "error")

    return redirect(url_for('manage_staff'))

@app.route('/toggle-admin', methods=['POST'])
def toggle_admin():
    staff_id = request.form['staff_id']
    action = request.form['action']  # Either "grant" or "revoke"
    
    try:
        if action == 'grant':
            update_admin_status(staff_id, True)
            flash(f"Staff with ID {staff_id} is now an Admin.", 'success')
        elif action == 'revoke':
            update_admin_status(staff_id, False)
            flash(f"Admin rights revoked for Staff with ID {staff_id}.", 'success')
        else:
            flash("Invalid action.", 'error')
    except Exception as e:
        flash(f"Error updating admin status: {e}", 'error')

    return redirect(url_for('manage_staff'))




@app.route('/generate-codes', methods=['GET'])
def generate_codes():
    try:
        # Fetch codes from engine
        class_codes = fetch_class_codes()
        staff_codes = fetch_staff_codes()

        # Render template with fetched data
        return render_template('class_codes.html', class_codes=class_codes, staff_codes=staff_codes)
    except Exception as e:
        flash(f"Error displaying codes: {e}", "error")
        return render_template('class_codes.html', class_codes=[], staff_codes=[])


@app.route('/generate-student-codes', methods=['POST'])
def generate_student_codes():
    try:
        batch_size = int(request.form.get('batch_size', 20))
        generate_class_codes(batch_size)
        flash(f"{batch_size} codes generated for each class.", "success")
        return redirect(url_for('generate_codes'))

    except Exception as e:
        flash(f"Error generating student codes: {e}", "error")
    return redirect(url_for('generate_codes'))

@app.route('/download-student-codes', methods=['GET'])
def download_student_codes():
    csv_data = fetch_class_codes_for_csv()  # Modify this to retrieve student-specific codes.
    if not csv_data:
        flash("No student codes available to download.", "error")
        return redirect(url_for('generate_codes'))

    # Create CSV response
    output = "\n".join([",".join(row) for row in csv_data])
    response = Response(output, mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=student_class_codes.csv"
    return response



@app.route('/generate-staff-codes', methods=['POST'])
def generate_staff_codes():
    try:
        generate_staff_verification_codes()  # Function to generate staff verification codes.
        flash("Staff verification codes generated successfully!", "success")
    except Exception as e:
        flash(f"Error generating staff codes: {e}", "error")
    return redirect(url_for('generate_codes'))

@app.route('/download-staff-codes', methods=['GET'])
def download_staff_codes():
    csv_data = fetch_staff_codes_for_csv()  # Modify this to retrieve staff-specific codes.
    if not csv_data:
        flash("No staff codes available to download.", "error")
        return redirect(url_for('generate_codes'))

    # Create CSV response
    output = "\n".join([",".join(row) for row in csv_data])
    response = Response(output, mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=staff_verification_codes.csv"
    return response



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80, use_reloader=True)
