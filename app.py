"""
BBS (Busia Bodaboda SACCO) Member Registration and Badge Generation System
Complete Flask Application with PostgreSQL, QR Codes, and Professional Badges
"""
import os
import logging
import zipfile
import re
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, send_from_directory, make_response
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, HiddenField, SelectField, BooleanField
from wtforms.validators import DataRequired, Length, Optional
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from config import config, Config
from database import (
    db, create_member, get_member, get_member_by_number,
    get_member_by_national_id, get_member_by_telephone,
    get_all_members, get_members_count, update_member,
    delete_member, get_recent_members,
    get_unissued_members, get_issued_members, log_badge_issuance,
    get_issuance_log,
    get_admin_by_id, get_admin_by_username,
    update_admin_password, log_admin_login,
    update_last_login
)
from utils.qr_generator import QRGenerator
from utils.image_processor import ImageProcessor
from utils.badge_generator import BadgeGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(config['production'])

# Enable ProxyFix for production
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Ensure directories exist
Config.ensure_directories()

# CSRF Protection
csrf = CSRFProtect(app)

# Initialize Bcrypt
bcrypt = Bcrypt(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access this page.'
login_manager.login_message_category = 'warning'
login_manager.session_protection = 'strong'

# Custom Jinja2 filter for datetime
@app.template_filter('datetime')
def format_datetime(value, format='%Y-%m-%d %H:%M'):
    if value is None:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return value
    return value.strftime(format)

@app.template_filter('datetime_iso')
def format_datetime_iso(value):
    if value is None:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return value
    return value.isoformat()

app.jinja_env.filters['datetime'] = format_datetime
app.jinja_env.filters['datetime_iso'] = format_datetime_iso

# Application context processor
@app.context_processor
def inject_config():
    return {
        'config': {
            'GROUP_NAME': Config.GROUP_NAME,
            'APP_NAME': Config.APP_NAME,
            'OFFICIAL_NAME': 'BBS (Busia Bodaboda SACCO)'
        },
        'current_user': current_user,
        'now': datetime.now(timezone.utc)
    }

# Security headers middleware
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; img-src 'self' data:; font-src 'self' https://cdnjs.cloudflare.com;"
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ----------------------------
# User Class for Flask-Login
# ----------------------------

class Admin(UserMixin):
    def __init__(self, admin_data):
        self.id = admin_data['id']
        self.username = admin_data['username']
        self.role = admin_data.get('role', 'admin')
        self.full_name = admin_data.get('full_name', '')
        self.email = admin_data.get('email', '')
        self._active = admin_data.get('is_active', True)
    
    @property
    def is_active(self):
        return self._active

@login_manager.user_loader
def load_user(user_id):
    admin = get_admin_by_id(int(user_id))
    if admin:
        return Admin(admin)
    return None

# ----------------------------
# Forms
# ----------------------------

class MemberRegistrationForm(FlaskForm):
    member_number = StringField('Member Number', validators=[DataRequired()])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=200)])
    national_id = StringField('National ID', validators=[DataRequired(), Length(min=5, max=20)])
    telephone = StringField('Telephone', validators=[DataRequired(), Length(min=10, max=15)])
    passport_photo = FileField('Passport Photo', validators=[Optional()])
    group_stage_name = StringField('Group/Stage Name', validators=[DataRequired()])
    chairman_name = StringField('Chairman Name', validators=[DataRequired()])
    chairman_phone = StringField('Chairman Phone', validators=[DataRequired()])
    motorcycle_registration = StringField('Motorcycle Registration', validators=[DataRequired()])
    next_of_kin_name = StringField('Next of Kin Name', validators=[DataRequired()])
    next_of_kin_phone = StringField('Next of Kin Phone', validators=[DataRequired()])
    date_registered = HiddenField('Date Registered')

class QRVerificationForm(FlaskForm):
    qr_data = StringField('QR Data', validators=[DataRequired()])

class BatchIssuanceForm(FlaskForm):
    format_type = SelectField('Print Format', choices=[('png', 'PNG'), ('pdf', 'PDF'), ('both', 'Both')])
    include_bleed = BooleanField('Include Bleed Area')
    print_quality = SelectField('Print Quality', choices=[('draft', 'Draft'), ('standard', 'Standard'), ('high', 'High')])

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = StringField('Password', validators=[DataRequired()])

# ----------------------------
# Authentication Routes
# ----------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data
        
        admin = get_admin_by_username(username)
        
        if admin and bcrypt.check_password_hash(admin['password_hash'], password):
            if admin.get('is_active', True):
                user = Admin(admin)
                login_user(user, remember=True, duration=timedelta(hours=8))
                update_last_login(admin['id'])
                log_admin_login(admin['id'], request.remote_addr, request.user_agent.string, True)
                flash(f'Welcome back, {admin.get("full_name", username)}!', 'success')
                
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('dashboard'))
            else:
                flash('Your account has been deactivated.', 'danger')
        else:
            if admin:
                log_admin_login(admin['id'], request.remote_addr, request.user_agent.string, False)
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

# ----------------------------
# Public Routes
# ----------------------------

@app.route('/')
def index():
    try:
        total_members = get_members_count()
        recent_members = get_recent_members(5)
        members = get_all_members(limit=1000)
        total_bodas = len([m for m in members if m.get('motorcycle_registration')])
        total_badges = len([m for m in members if m.get('badge_image')])
        unissued = len(get_unissued_members())

        return render_template('index.html',
                             total_members=total_members,
                             recent_members=recent_members,
                             total_bodas=total_bodas,
                             total_badges=total_badges,
                             unissued_badges=unissued)
    except Exception as e:
        logger.error(f"Error loading index: {e}")
        flash('Error loading dashboard data.', 'danger')
        return render_template('index.html', total_members=0, recent_members=[])

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    form = MemberRegistrationForm()
    now = datetime.now(timezone.utc)

    if form.validate_on_submit():
        try:
            data = {
                'member_number': form.member_number.data.upper().strip(),
                'full_name': form.full_name.data.strip().title(),
                'national_id': form.national_id.data.strip(),
                'telephone': form.telephone.data.strip(),
                'group_stage_name': form.group_stage_name.data.strip().title(),
                'chairman_name': form.chairman_name.data.strip().title(),
                'chairman_phone': form.chairman_phone.data.strip(),
                'motorcycle_registration': form.motorcycle_registration.data.strip().upper(),
                'next_of_kin_name': form.next_of_kin_name.data.strip().title(),
                'next_of_kin_phone': form.next_of_kin_phone.data.strip(),
                'date_registered': now.strftime('%Y-%m-%d'),
                'passport_photo': None,
                'qr_code_data': None,
                'badge_image': None,
                'badge_issued': False,
                'badge_issued_date': None,
                'badge_issued_by': None
            }

            if get_member_by_number(data['member_number']):
                flash(f'Member number {data["member_number"]} already exists.', 'danger')
                return render_template('register.html', form=form)

            if get_member_by_national_id(data['national_id']):
                flash(f'National ID {data["national_id"]} already registered.', 'danger')
                return render_template('register.html', form=form)

            if get_member_by_telephone(data['telephone']):
                flash(f'Telephone number {data["telephone"]} already registered.', 'danger')
                return render_template('register.html', form=form)

            # Handle photo upload or camera capture
            photo_processed = False
            if 'passport_photo' in request.files:
                file = request.files['passport_photo']
                if file and file.filename:
                    if ImageProcessor.validate_image(file):
                        filename, filepath = ImageProcessor.save_uploaded_file(file, data['member_number'])
                        data['passport_photo'] = filename
                        photo_processed = True
                    else:
                        flash('Invalid photo file. Please upload a JPG, JPEG, or PNG image.', 'danger')
                        return render_template('register.html', form=form)
            
            # Check for camera captured image (base64 data from canvas)
            camera_photo = request.form.get('camera_photo_data')
            if camera_photo and not photo_processed:
                try:
                    import base64
                    from io import BytesIO
                    from PIL import Image
                    
                    # Decode base64 image data
                    if 'data:image' in camera_photo:
                        # Remove data URL prefix
                        header, encoded = camera_photo.split(',', 1)
                        image_data = base64.b64decode(encoded)
                    else:
                        image_data = base64.b64decode(camera_photo)
                    
                    # Create PIL image
                    img = Image.open(BytesIO(image_data))
                    
                    # Ensure RGB mode
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Process image through the same pipeline as uploaded images
                    filename = f"{data['member_number']}.jpg"
                    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
                    
                    # Save with proper orientation
                    img = ImageProcessor.normalize_orientation(img)
                    
                    # Resize to passport photo dimensions
                    img = ImageProcessor.resize_passport_photo_from_image(img, dpi=Config.BADGE_DPI)
                    
                    # Save
                    img.save(filepath, 'JPEG', quality=95, optimize=True, dpi=(Config.BADGE_DPI, Config.BADGE_DPI))
                    
                    # Create thumbnail
                    thumb_filename = f"{data['member_number']}_thumb.jpg"
                    thumb_path = os.path.join(Config.UPLOAD_FOLDER, thumb_filename)
                    thumb = img.copy()
                    thumb.thumbnail((150, 180), Image.LANCZOS)
                    thumb.save(thumb_path, 'JPEG', quality=85, optimize=True)
                    
                    data['passport_photo'] = filename
                    photo_processed = True
                    
                    logger.info(f"Camera photo captured and stored for member: {data['member_number']}")
                except Exception as e:
                    logger.error(f"Error processing camera photo: {e}")
                    flash('Error processing camera photo. Please try again or upload a photo.', 'danger')
                    return render_template('register.html', form=form)

            try:
                qr_path, qr_filename = QRGenerator.generate_qr(data)
                data['qr_code_data'] = qr_path
            except Exception as e:
                logger.error(f"Error generating QR code: {e}")
                flash('Error generating QR code. Please try again.', 'danger')
                return render_template('register.html', form=form)

            member_id = create_member(data)
            member = get_member(member_id)

            if member:
                try:
                    badge_path, badge_filename = BadgeGenerator.generate_badge(member, include_bleed=True)
                    update_member(member_id, {'badge_image': badge_filename})
                    flash(f'Member {data["full_name"]} registered successfully with badge!', 'success')
                except Exception as e:
                    logger.error(f"Error generating badge: {e}")
                    flash('Member registered but badge generation failed. You can regenerate later.', 'warning')
            else:
                flash('Member registered but could not retrieve data.', 'warning')

            return redirect(url_for('view_badge', member_id=member_id))

        except Exception as e:
            logger.error(f"Error registering member: {e}")
            flash('Error registering member. Please try again.', 'danger')

    return render_template('register.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        filter_type = request.args.get('filter', 'all')
        per_page = 20
        offset = (page - 1) * per_page

        if filter_type == 'issued':
            members = get_issued_members(per_page)
            total = len(get_issued_members())
        elif filter_type == 'unissued':
            members = get_unissued_members(per_page)
            total = len(get_unissued_members())
        else:
            members = get_all_members(per_page, offset, search)
            total = get_members_count(search)

        total_pages = (total + per_page - 1) // per_page if total > 0 else 1

        all_members = get_all_members(limit=1000)
        total_badges = len([m for m in all_members if m.get('badge_image')])
        unissued = len(get_unissued_members())
        issued = len(get_issued_members())
        groups = set([m.get('group_stage_name') for m in all_members if m.get('group_stage_name')])
        recent = get_recent_members(10)

        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_num': page - 1 if page > 1 else 1,
            'next_num': page + 1 if page < total_pages else total_pages
        }

        return render_template('dashboard.html',
                             members=members,
                             pagination=pagination,
                             search_query=search,
                             filter_type=filter_type,
                             total_members=total,
                             total_badges=total_badges,
                             total_groups=len(groups),
                             unissued_badges=unissued,
                             issued_badges=issued,
                             recent_members=recent)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        flash('Error loading dashboard.', 'danger')
        return render_template('dashboard.html', members=[], pagination={'total': 0})

@app.route('/member/edit/<int:member_id>', methods=['GET', 'POST'])
@login_required
def edit_member(member_id):
    member = get_member(member_id)
    if not member:
        flash('Member not found.', 'danger')
        return redirect(url_for('dashboard'))

    form = MemberRegistrationForm()

    if form.validate_on_submit():
        try:
            data = {
                'member_number': form.member_number.data.upper().strip(),
                'full_name': form.full_name.data.strip().title(),
                'national_id': form.national_id.data.strip(),
                'telephone': form.telephone.data.strip(),
                'group_stage_name': form.group_stage_name.data.strip().title(),
                'chairman_name': form.chairman_name.data.strip().title(),
                'chairman_phone': form.chairman_phone.data.strip(),
                'motorcycle_registration': form.motorcycle_registration.data.strip().upper(),
                'next_of_kin_name': form.next_of_kin_name.data.strip().title(),
                'next_of_kin_phone': form.next_of_kin_phone.data.strip()
            }

            existing = get_member_by_number(data['member_number'])
            if existing and existing['id'] != member_id:
                flash(f'Member number {data["member_number"]} already exists.', 'danger')
                return render_template('edit_member.html', form=form, member=member)

            existing = get_member_by_national_id(data['national_id'])
            if existing and existing['id'] != member_id:
                flash(f'National ID {data["national_id"]} already registered.', 'danger')
                return render_template('edit_member.html', form=form, member=member)

            existing = get_member_by_telephone(data['telephone'])
            if existing and existing['id'] != member_id:
                flash(f'Telephone number {data["telephone"]} already registered.', 'danger')
                return render_template('edit_member.html', form=form, member=member)

            # Handle photo upload
            if 'passport_photo' in request.files:
                file = request.files['passport_photo']
                if file and file.filename:
                    if ImageProcessor.validate_image(file):
                        filename, filepath = ImageProcessor.save_uploaded_file(file, data['member_number'])
                        data['passport_photo'] = filename
                    else:
                        flash('Invalid photo file. Please upload a JPG, JPEG, or PNG image.', 'danger')
                        return render_template('edit_member.html', form=form, member=member)

            # Handle camera capture on edit
            camera_photo = request.form.get('camera_photo_data')
            if camera_photo and 'passport_photo' not in data:
                try:
                    import base64
                    from io import BytesIO
                    from PIL import Image
                    
                    if 'data:image' in camera_photo:
                        header, encoded = camera_photo.split(',', 1)
                        image_data = base64.b64decode(encoded)
                    else:
                        image_data = base64.b64decode(camera_photo)
                    
                    img = Image.open(BytesIO(image_data))
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    filename = f"{data['member_number']}.jpg"
                    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
                    
                    img = ImageProcessor.normalize_orientation(img)
                    img = ImageProcessor.resize_passport_photo_from_image(img, dpi=Config.BADGE_DPI)
                    
                    img.save(filepath, 'JPEG', quality=95, optimize=True, dpi=(Config.BADGE_DPI, Config.BADGE_DPI))
                    
                    thumb_filename = f"{data['member_number']}_thumb.jpg"
                    thumb_path = os.path.join(Config.UPLOAD_FOLDER, thumb_filename)
                    thumb = img.copy()
                    thumb.thumbnail((150, 180), Image.LANCZOS)
                    thumb.save(thumb_path, 'JPEG', quality=85, optimize=True)
                    
                    data['passport_photo'] = filename
                except Exception as e:
                    logger.error(f"Error processing camera photo in edit: {e}")
                    flash('Error processing camera photo.', 'danger')
                    return render_template('edit_member.html', form=form, member=member)

            update_member(member_id, data)
            updated_member = get_member(member_id)
            if updated_member:
                badge_path, badge_filename = BadgeGenerator.generate_badge(updated_member, include_bleed=True)
                update_member(member_id, {'badge_image': badge_filename})

            flash('Member details updated successfully!', 'success')
            return redirect(url_for('view_badge', member_id=member_id))

        except Exception as e:
            logger.error(f"Error updating member: {e}")
            flash('Error updating member. Please try again.', 'danger')

    form.member_number.data = member['member_number']
    form.full_name.data = member['full_name']
    form.national_id.data = member['national_id']
    form.telephone.data = member['telephone']
    form.group_stage_name.data = member['group_stage_name']
    form.chairman_name.data = member['chairman_name']
    form.chairman_phone.data = member['chairman_phone']
    form.motorcycle_registration.data = member['motorcycle_registration']
    form.next_of_kin_name.data = member['next_of_kin_name']
    form.next_of_kin_phone.data = member['next_of_kin_phone']

    return render_template('edit_member.html', form=form, member=member)

@app.route('/member/delete/<int:member_id>', methods=['POST'])
@login_required
def delete_member_route(member_id):
    try:
        member = get_member(member_id)
        if not member:
            return jsonify({'success': False, 'error': 'Member not found'}), 404

        if member.get('passport_photo'):
            photo_path = os.path.join(Config.UPLOAD_FOLDER, member['passport_photo'])
            if os.path.exists(photo_path):
                os.remove(photo_path)
            thumb_path = os.path.join(Config.UPLOAD_FOLDER, f"{member['member_number']}_thumb.jpg")
            if os.path.exists(thumb_path):
                os.remove(thumb_path)

        if member.get('badge_image'):
            badge_path = os.path.join(Config.BADGE_FOLDER, member['badge_image'])
            if os.path.exists(badge_path):
                os.remove(badge_path)

        qr_path = os.path.join(Config.QR_FOLDER, f"qr_{member['member_number']}.png")
        if os.path.exists(qr_path):
            os.remove(qr_path)

        delete_member(member_id)
        flash('Member deleted successfully.', 'success')
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error deleting member: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/badge/<int:member_id>')
@login_required
def view_badge(member_id):
    member = get_member(member_id)
    if not member:
        flash('Member not found.', 'danger')
        return redirect(url_for('dashboard'))

    issuance_log = get_issuance_log(member_id, 10)
    return render_template('badge.html', member=member, issuance_log=issuance_log)

@app.route('/badge/download/<int:member_id>')
@login_required
def download_badge(member_id):
    member = get_member(member_id)
    if not member:
        flash('Member not found.', 'danger')
        return redirect(url_for('dashboard'))

    format_type = request.args.get('format', 'png')
    include_bleed = request.args.get('bleed', 'false').lower() == 'true'

    badge_filename = member.get('badge_image')
    if not badge_filename:
        try:
            badge_path, badge_filename = BadgeGenerator.generate_badge(member, include_bleed=include_bleed)
            update_member(member_id, {'badge_image': badge_filename})
        except Exception as e:
            logger.error(f"Error generating badge: {e}")
            flash('Error generating badge.', 'danger')
            return redirect(url_for('view_badge', member_id=member_id))

    badge_path = os.path.join(Config.BADGE_FOLDER, badge_filename)
    if not os.path.exists(badge_path):
        flash('Badge file not found.', 'danger')
        return redirect(url_for('view_badge', member_id=member_id))

    now = datetime.now(timezone.utc)
    
    if format_type == 'pdf':
        log_badge_issuance(member_id, current_user.username, format_type, 'high')
        try:
            pdf_path, pdf_filename = BadgeGenerator.generate_pdf_badge(member, include_bleed=include_bleed)
            return send_file(pdf_path, as_attachment=True, download_name=f"badge_{member['member_number']}.pdf", mimetype='application/pdf')
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            flash('Error generating PDF badge.', 'danger')
            return redirect(url_for('view_badge', member_id=member_id))

    log_badge_issuance(member_id, current_user.username, 'png', 'high')
    update_member(member_id, {
        'badge_issued': True,
        'badge_issued_date': now,
        'badge_issued_by': current_user.username,
        'badge_print_count': (member.get('badge_print_count', 0) + 1),
        'last_printed': now
    })

    return send_file(badge_path, as_attachment=True, download_name=f"badge_{member['member_number']}.png", mimetype='image/png')

@app.route('/badge/regenerate/<int:member_id>')
@login_required
def regenerate_badge(member_id):
    member = get_member(member_id)
    if not member:
        flash('Member not found.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        if member.get('badge_image'):
            old_badge_path = os.path.join(Config.BADGE_FOLDER, member['badge_image'])
            if os.path.exists(old_badge_path):
                os.remove(old_badge_path)

        badge_path, badge_filename = BadgeGenerator.generate_badge(member, include_bleed=True)
        update_member(member_id, {'badge_image': badge_filename})
        flash('Badge regenerated successfully!', 'success')
    except Exception as e:
        logger.error(f"Error regenerating badge: {e}")
        flash('Error regenerating badge.', 'danger')

    return redirect(url_for('view_badge', member_id=member_id))

@app.route('/badge/issue/<int:member_id>', methods=['POST'])
@login_required
def issue_badge(member_id):
    member = get_member(member_id)
    if not member:
        return jsonify({'success': False, 'error': 'Member not found'}), 404

    try:
        now = datetime.now(timezone.utc)
        update_member(member_id, {
            'badge_issued': True,
            'badge_issued_date': now,
            'badge_issued_by': request.form.get('issued_by', current_user.username),
            'badge_print_count': (member.get('badge_print_count', 0) + 1),
            'last_printed': now
        })

        log_badge_issuance(
            member_id,
            request.form.get('issued_by', current_user.username),
            request.form.get('format', 'standard'),
            request.form.get('quality', 'high'),
            request.form.get('notes', 'Manual issuance')
        )

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error issuing badge: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/badge/batch', methods=['GET', 'POST'])
@login_required
def batch_badges():
    form = BatchIssuanceForm()
    unissued_members = get_unissued_members()
    unissued_count = len(unissued_members)
    issued_count = len(get_issued_members())

    if form.validate_on_submit():
        try:
            members = get_unissued_members()
            if not members:
                flash('No unissued members found.', 'warning')
                return redirect(url_for('batch_badges'))

            format_type = form.format_type.data
            include_bleed = form.include_bleed.data
            print_quality = form.print_quality.data

            results = BadgeGenerator.generate_batch_badges(members, include_bleed=include_bleed)

            now = datetime.now(timezone.utc)
            for member in members:
                if results.get(member['member_number'], {}).get('success'):
                    log_badge_issuance(
                        member['id'],
                        current_user.username,
                        format_type,
                        print_quality,
                        f'Batch issuance on {now.strftime("%Y-%m-%d")}'
                    )
                    update_member(member['id'], {
                        'badge_issued': True,
                        'badge_issued_date': now,
                        'badge_issued_by': current_user.username,
                        'badge_print_count': (member.get('badge_print_count', 0) + 1),
                        'last_printed': now
                    })

            success_count = sum(1 for r in results.values() if r.get('success'))
            flash(f'Successfully generated {success_count} badges out of {len(members)} members.', 'success')

            if format_type in ['pdf', 'both']:
                zip_filename = f"badges_{now.strftime('%Y%m%d_%H%M%S')}.zip"
                zip_path = os.path.join(Config.EXPORT_FOLDER, zip_filename)

                with zipfile.ZipFile(zip_path, 'w') as zip_file:
                    for member in members:
                        member_num = member['member_number']
                        if format_type in ['pdf', 'both']:
                            pdf_path = os.path.join(Config.EXPORT_FOLDER, f"badge_{member_num}.pdf")
                            if os.path.exists(pdf_path):
                                zip_file.write(pdf_path, f"badge_{member_num}.pdf")
                        if format_type in ['png', 'both']:
                            png_path = os.path.join(Config.BADGE_FOLDER, f"badge_{member_num}.png")
                            if os.path.exists(png_path):
                                zip_file.write(png_path, f"badge_{member_num}.png")

                return send_file(zip_path, as_attachment=True, download_name=zip_filename, mimetype='application/zip')

            return redirect(url_for('dashboard'))

        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            flash('Error processing batch badges.', 'danger')

    return render_template('batch_badges.html', 
                         form=form, 
                         unissued_count=unissued_count, 
                         issued_count=issued_count,
                         unissued_members=unissued_members[:20])

@app.route('/verify-qr', methods=['GET', 'POST'])
def verify_qr():
    form = QRVerificationForm()
    member = None
    error = None

    if form.validate_on_submit():
        try:
            qr_data = form.qr_data.data.strip()
            lines = qr_data.split('\n')
            member_number = None

            for line in lines:
                if line.startswith('Member:'):
                    member_number = line.replace('Member:', '').strip()
                    break

            if member_number:
                member = get_member_by_number(member_number)
                if not member:
                    error = 'Member not found. Please check the QR code data.'
            else:
                error = 'Invalid QR code data format.'

        except Exception as e:
            logger.error(f"Error verifying QR: {e}")
            error = 'Error verifying QR code. Please try again.'

    return render_template('verify_qr.html', form=form, member=member, error=error)

@app.route('/export/members')
@login_required
def export_members():
    format_type = request.args.get('format', 'csv')
    member_ids = request.args.getlist('ids')

    try:
        if member_ids:
            members = [get_member(int(id)) for id in member_ids if id]
        else:
            members = get_all_members(limit=10000)

        if format_type == 'csv':
            import csv
            from io import StringIO

            output = StringIO()
            writer = csv.writer(output)
            headers = ['Member Number', 'Full Name', 'National ID', 'Telephone',
                      'Group', 'Chairman', 'Badge Issued', 'Date Registered']
            writer.writerow(headers)

            for m in members:
                writer.writerow([
                    m['member_number'], m['full_name'], m['national_id'],
                    m['telephone'], m['group_stage_name'], m['chairman_name'],
                    'Yes' if m.get('badge_issued') else 'No',
                    m.get('date_registered', '')
                ])

            output.seek(0)
            return send_file(StringIO(output.getvalue()), as_attachment=True, download_name=f"members_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv", mimetype='text/csv')

        flash(f'Export format {format_type} not supported yet.', 'warning')
        return redirect(url_for('dashboard'))

    except Exception as e:
        logger.error(f"Error exporting members: {e}")
        flash('Error exporting members.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'group': Config.GROUP_NAME,
        'official_name': 'BBS (Busia Bodaboda SACCO)',
        'features': {
            'badge_generation': True,
            'qr_codes': True,
            'batch_issuance': True,
            'print_ready': True,
            'authentication': True
        }
    })

# ============================================================
# LEGAL DOCUMENT ROUTES
# ============================================================

@app.route('/legal')
def legal_documents():
    return render_template('legal.html')

@app.route('/legal/terms')
def legal_terms():
    return send_from_directory('legal', 'terms_of_service.md', mimetype='text/markdown')

@app.route('/legal/privacy')
def legal_privacy():
    return send_from_directory('legal', 'privacy_policy.md', mimetype='text/markdown')

@app.route('/legal/eula')
def legal_eula():
    return send_from_directory('legal', 'eula.md', mimetype='text/markdown')

@app.route('/legal/user-manual')
def legal_user_manual():
    return send_from_directory('legal', 'user_manual.md', mimetype='text/markdown')

@app.route('/legal/admin-guide')
def legal_admin_guide():
    return send_from_directory('legal', 'admin_guide.md', mimetype='text/markdown')

@app.route('/legal/acceptable-use')
def legal_acceptable_use():
    return send_from_directory('legal', 'acceptable_use_policy.md', mimetype='text/markdown')

@app.route('/legal/consent')
def legal_consent():
    return send_from_directory('legal', 'consent_form.md', mimetype='text/markdown')

# ----------------------------
# Error Handlers
# ----------------------------

@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return render_template('base.html'), 500

# ----------------------------
# Application Entry Point
# ----------------------------

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config.get('DEBUG', False))
