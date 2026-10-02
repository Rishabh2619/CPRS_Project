import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'coer-cprs-secret-key-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads', 'resumes')

# Ensure upload directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)

# --- Database Models ---

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(20), unique=True)
    branch = db.Column(db.String(50))
    cgpa = db.Column(db.Float)
    skills = db.Column(db.Text)
    resume_path = db.Column(db.String(256))
    role = db.Column(db.String(20), default='student')  # student, staff, admin

class Job(db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    requirements = db.Column(db.Text)
    location = db.Column(db.String(100))
    salary = db.Column(db.String(50))
    posted_date = db.Column(db.DateTime, default=datetime.utcnow)

class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    applied_date = db.Column(db.DateTime, default=datetime.utcnow)

# --- Authentication Routes ---

@app.route('/')
def homepage():
    return render_template('homepage.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['name'] = user.name
            flash('Login successful!', 'success')
            
            if user.role == 'student':
                return redirect(url_for('dashboard'))
            elif user.role == 'staff':
                return redirect(url_for('staff_dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid email or password', 'error')
            
    return render_template('login.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email, role='admin').first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['role'] = 'admin'
            session['name'] = user.name
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid Admin credentials', 'error')
            
    return render_template('admin_login.html')

@app.route('/staff_login', methods=['GET', 'POST'])
def staff_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email, role='staff').first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['role'] = 'staff'
            session['name'] = user.name
            return redirect(url_for('staff_dashboard'))
        else:
            flash('Invalid Staff credentials', 'error')
            
    return render_template('staff_login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        roll_number = request.form.get('roll_number')
        branch = request.form.get('branch')
        cgpa = request.form.get('cgpa')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        
        new_user = User(
            email=email,
            password_hash=hashed_password,
            name=name,
            roll_number=roll_number,
            branch=branch,
            cgpa=float(cgpa) if cgpa else 0.0,
            role='student'
        )
        
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('homepage'))

# --- Student Routes ---

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    
    user = db.session.get(User, session['user_id'])
    jobs = Job.query.all()
    my_apps = {app.job_id: app.status for app in Application.query.filter_by(student_id=session['user_id']).all()}
    
    return render_template('dashboard.html', user=user, jobs=jobs, my_apps=my_apps)

@app.route('/apply/<int:job_id>')
def apply_job(job_id):
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    
    existing = Application.query.filter_by(student_id=session['user_id'], job_id=job_id).first()
    
    if existing:
        flash('You have already applied for this job.', 'error')
    else:
        new_app = Application(student_id=session['user_id'], job_id=job_id, status='Pending')
        db.session.add(new_app)
        db.session.commit()
        flash('Application submitted successfully!', 'success')
        
    return redirect(url_for('dashboard'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.session.get(User, session['user_id'])
    
    if request.method == 'POST':
        user.branch = request.form.get('branch')
        cgpa_val = request.form.get('cgpa')
        if cgpa_val:
            user.cgpa = float(cgpa_val)
        user.skills = request.form.get('skills')
        
        if 'resume' in request.files:
            file = request.files['resume']
            if file and file.filename != '':
                safe_name = secure_filename(file.filename)
                filename = f"{user.roll_number or user.id}_{safe_name}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                user.resume_path = filename
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        
    return render_template('profile.html', user=user)

# --- Staff & Admin Management Routes ---

@app.route('/staff_dashboard')
def staff_dashboard():
    if 'user_id' not in session or session.get('role') != 'staff':
        return redirect(url_for('staff_login'))
    
    jobs = Job.query.all()
    return render_template('staff_dashboard.html', jobs=jobs)

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('admin_login'))
    
    students = User.query.filter_by(role='student').all()
    total_jobs = Job.query.count()
    total_apps = Application.query.count()
    
    return render_template('admin_dashboard.html', students=students, total_jobs=total_jobs, total_apps=total_apps)

@app.route('/admin_create_placement', methods=['GET', 'POST'])
def admin_create_placement():
    if 'user_id' not in session or session.get('role') not in ['staff', 'admin']:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        new_job = Job(
            title=request.form.get('title'),
            company=request.form.get('company'),
            description=request.form.get('description'),
            requirements=request.form.get('requirements'),
            location=request.form.get('location'),
            salary=request.form.get('salary')
        )
        db.session.add(new_job)
        db.session.commit()
        flash('Job posted successfully!', 'success')
        return redirect(url_for('staff_dashboard'))
        
    return render_template('admin_create_placement.html')

@app.route('/admin/manage_placements')
def admin_manage_placements():
    if 'user_id' not in session or session.get('role') not in ['admin', 'staff']:
        return redirect(url_for('login'))
    
    jobs = Job.query.all()
    return render_template('admin_manage_placements.html', jobs=jobs)

@app.route('/staff/delete_placement/<int:job_id>')
def staff_delete_placement(job_id):
    if 'user_id' not in session or session.get('role') not in ['admin', 'staff']:
        return redirect(url_for('login'))
        
    job = db.session.get(Job, job_id)
    if job:
        Application.query.filter_by(job_id=job_id).delete()
        db.session.delete(job)
        db.session.commit()
        flash('Job deleted successfully!', 'success')
    return redirect(url_for('admin_manage_placements'))

@app.route('/admin/create_student', methods=['GET', 'POST'])
def admin_create_student():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('admin_create_student'))
            
        new_student = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            role='student'
        )
        db.session.add(new_student)
        db.session.commit()
        flash('Student account created successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
        
    return render_template('admin_create_student.html')

@app.route('/admin/manage_news')
def admin_manage_news():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    return render_template('admin_manage_news.html')

@app.route('/admin/update_results/<int:job_id>', methods=['GET', 'POST'])
def admin_update_results(job_id):
    if 'user_id' not in session or session.get('role') not in ['admin', 'staff']:
        return redirect(url_for('login'))
        
    job = db.session.get(Job, job_id)
    applications = db.session.query(Application, User).join(User, Application.student_id == User.id).filter(Application.job_id == job_id).all()
    
    if request.method == 'POST':
        app_id = request.form.get('application_id')
        new_status = request.form.get('status')
        app_obj = db.session.get(Application, app_id)
        if app_obj:
            app_obj.status = new_status
            db.session.commit()
            flash('Application status updated!', 'success')
            
    return render_template('admin_update_results.html', job=job, applications=applications)

# --- Database Setup ---
with app.app_context():
    db.create_all()
    admin = User.query.filter_by(email='admin@coer.ac.in').first()
    if not admin:
        admin = User(
            email='admin@coer.ac.in',
            password_hash=generate_password_hash('Admin@123'),
            name='Administrator',
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)