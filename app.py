"""
Bodaboda SACCO Member Registration and Badge Generation System
Complete Flask Application with PostgreSQL, QR Codes, and Professional Badges
"""
import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, HiddenField
from wtforms.validators import DataRequired, Length, Regexp

from config import config, Config
from database import (
    db, create_member, get_member, get_member_by_number,
    get_member_by_national_id, get_member_by_telephone,
    get_all_members, get_members_count, update_member,
    delete_member, get_recent_members, search_members_by_qr
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

# Ensure directories exist
Config.ensure_directories()

# CSRF Protection
csrf = CSRFProtect(app)

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

# Register custom filter
app.jinja_env.filters['datetime'] = format_datetime

# Application context processor
@app.context_processor
def inject_config():
    """Inject configuration into templates"""
    return {
        'config': {
            'GROUP_NAME': Config.GROUP_NAME,
            'APP_NAME': Config.APP_NAME
        }
    }

# ----------------------------
# Forms
# ----------------------------

class MemberRegistrationForm(FlaskForm):
    """Member registration form"""
    member_number = StringField('Member Number', validators=[DataRequired()])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=200)])
    national_id = StringField('National ID', validators=[DataRequired(), Length(min=5, max=20)])
    telephone = StringField('Telephone', validators=[DataRequired(), Length(min=10, max=15)])
    passport_photo = FileField('Passport Photo')
    group_stage_name = StringField('Group/Stage Name', validators=[DataRequired()])
    chairman_name = StringField('Chairman Name', validators=[DataRequired()])
    chairman_phone = StringField('Chairman Phone', validators=[DataRequired()])
    motorcycle_registration = StringField('Motorcycle Registration', validators=[DataRequired()])
    next_of_kin_name = StringField('Next of Kin Name', validators=[DataRequired()])
    next_of_kin_phone = StringField('Next of Kin Phone', validators=[DataRequired()])
    date_registered = HiddenField('Date Registered')

class QRVerificationForm(FlaskForm):
    """QR code verification form"""
    qr_data = StringField('QR Data', validators=[DataRequired()])

# ----------------------------
# Routes
# ----------------------------

@app.route('/')
def index():
    """Home page"""
    try:
        total_members = get_members_count()
        recent_members = get_recent_members(5)
        
        # Calculate additional stats
        members = get_all_members(limit=1000)
        total_bodas = len([m for m in members if m.get('motorcycle_registration')])
        total_badges = len([m for m in members if m.get('badge_image')])
        
        return render_template('index.html', 
                             total_members=total_members,
                             recent_members=recent_members,
                             total_bodas=total_bodas,
                             total_badges=total_badges)
    except Exception as e:
        logger.error(f"Error loading index: {e}")
        flash('Error loading dashboard data.', 'danger')
        return render_template('index.html', total_members=0, recent_members=[])

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new member"""
    form = MemberRegistrationForm()
    
    if request.method == 'POST' and form.validate_on_submit():
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
                'date_registered': datetime.now().strftime('%Y-%m-%d'),
                'passport_photo': None,
                'qr_code_data': None,
                'badge_image': None
            }
            
            # Check for duplicates
            if get_member_by_number(data['member_number']):
                flash(f'Member number {data["member_number"]} already exists.', 'danger')
                return render_template('register.html', form=form)
            
            if get_member_by_national_id(data['national_id']):
                flash(f'National ID {data["national_id"]} already registered.', 'danger')
                return render_template('register.html', form=form)
            
            if get_member_by_telephone(data['telephone']):
                flash(f'Telephone number {data["telephone"]} already registered.', 'danger')
                return render_template('register.html', form=form)
            
            # Handle passport photo
            if 'passport_photo' in request.files:
                file = request.files['passport_photo']
                if file and file.filename:
                    if ImageProcessor.validate_image(file):
                        filename, filepath = ImageProcessor.save_uploaded_file(file, data['member_number'])
                        data['passport_photo'] = filename
                    else:
                        flash('Invalid photo file. Please upload a JPG, JPEG, or PNG image.', 'danger')
                        return render_template('register.html', form=form)
            
            # Generate QR code
            try:
                qr_path, qr_filename = QRGenerator.generate_qr(data)
                data['qr_code_data'] = qr_path
            except Exception as e:
                logger.error(f"Error generating QR code: {e}")
                flash('Error generating QR code. Please try again.', 'danger')
                return render_template('register.html', form=form)
            
            # Create member
            member_id = create_member(data)
            
            # Generate badge
            try:
                member = get_member(member_id)
                badge_path, badge_filename = BadgeGenerator.generate_badge(member)
                
                # Update member with badge image
                update_member(member_id, {'badge_image': badge_filename})
            except Exception as e:
                logger.error(f"Error generating badge: {e}")
                flash('Member registered but badge generation failed. You can regenerate later.', 'warning')
            
            flash(f'Member {data["full_name"]} registered successfully!', 'success')
            return redirect(url_for('view_badge', member_id=member_id))
            
        except Exception as e:
            logger.error(f"Error registering member: {e}")
            flash('Error registering member. Please try again.', 'danger')
    
    return render_template('register.html', form=form)

@app.route('/dashboard')
def dashboard():
    """Member dashboard with search and pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        per_page = 20
        offset = (page - 1) * per_page
        
        members = get_all_members(per_page, offset, search)
        total = get_members_count(search)
        
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        
        # Get stats
        all_members = get_all_members(limit=1000)
        total_badges = len([m for m in all_members if m.get('badge_image')])
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
                             total_members=total,
                             total_badges=total_badges,
                             total_groups=len(groups),
                             recent_members=recent)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        flash('Error loading dashboard.', 'danger')
        return render_template('dashboard.html', members=[], pagination={'total': 0})

@app.route('/member/edit/<int:member_id>', methods=['GET', 'POST'])
def edit_member(member_id):
    """Edit member details"""
    member = get_member(member_id)
    if not member:
        flash('Member not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = MemberRegistrationForm()
    
    if request.method == 'POST' and form.validate_on_submit():
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
            
            # Check for duplicate member number (excluding current member)
            existing = get_member_by_number(data['member_number'])
            if existing and existing['id'] != member_id:
                flash(f'Member number {data["member_number"]} already exists.', 'danger')
                return render_template('edit_member.html', form=form, member=member)
            
            # Check for duplicate national ID
            existing = get_member_by_national_id(data['national_id'])
            if existing and existing['id'] != member_id:
                flash(f'National ID {data["national_id"]} already registered.', 'danger')
                return render_template('edit_member.html', form=form, member=member)
            
            # Check for duplicate telephone
            existing = get_member_by_telephone(data['telephone'])
            if existing and existing['id'] != member_id:
                flash(f'Telephone number {data["telephone"]} already registered.', 'danger')
                return render_template('edit_member.html', form=form, member=member)
            
            # Handle passport photo
            if 'passport_photo' in request.files:
                file = request.files['passport_photo']
                if file and file.filename:
                    if ImageProcessor.validate_image(file):
                        filename, filepath = ImageProcessor.save_uploaded_file(file, data['member_number'])
                        data['passport_photo'] = filename
                    else:
                        flash('Invalid photo file. Please upload a JPG, JPEG, or PNG image.', 'danger')
                        return render_template('edit_member.html', form=form, member=member)
            
            # Update member
            update_member(member_id, data)
            
            # Regenerate badge with updated info
            updated_member = get_member(member_id)
            badge_path, badge_filename = BadgeGenerator.generate_badge(updated_member)
            update_member(member_id, {'badge_image': badge_filename})
            
            flash('Member details updated successfully!', 'success')
            return redirect(url_for('view_badge', member_id=member_id))
            
        except Exception as e:
            logger.error(f"Error updating member: {e}")
            flash('Error updating member. Please try again.', 'danger')
    
    # Populate form with member data
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
def delete_member_route(member_id):
    """Delete a member"""
    try:
        member = get_member(member_id)
        if not member:
            return jsonify({'success': False, 'error': 'Member not found'}), 404
        
        # Delete photo files
        if member.get('passport_photo'):
            photo_path = os.path.join(Config.UPLOAD_FOLDER, member['passport_photo'])
            if os.path.exists(photo_path):
                os.remove(photo_path)
            
            thumb_path = os.path.join(Config.UPLOAD_FOLDER, 
                                     f"{member['member_number']}_thumb.jpg")
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
        
        # Delete badge
        if member.get('badge_image'):
            badge_path = os.path.join(Config.BADGE_FOLDER, member['badge_image'])
            if os.path.exists(badge_path):
                os.remove(badge_path)
        
        # Delete QR code
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
def view_badge(member_id):
    """View member badge"""
    member = get_member(member_id)
    if not member:
        flash('Member not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('badge.html', member=member)

@app.route('/badge/download/<int:member_id>')
def download_badge(member_id):
    """Download member badge as PNG"""
    member = get_member(member_id)
    if not member:
        flash('Member not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    badge_filename = member.get('badge_image')
    if not badge_filename:
        # Generate badge if it doesn't exist
        try:
            badge_path, badge_filename = BadgeGenerator.generate_badge(member)
            update_member(member_id, {'badge_image': badge_filename})
        except Exception as e:
            logger.error(f"Error generating badge: {e}")
            flash('Error generating badge.', 'danger')
            return redirect(url_for('view_badge', member_id=member_id))
    
    badge_path = os.path.join(Config.BADGE_FOLDER, badge_filename)
    if not os.path.exists(badge_path):
        flash('Badge file not found.', 'danger')
        return redirect(url_for('view_badge', member_id=member_id))
    
    return send_file(badge_path, 
                    as_attachment=True,
                    download_name=f"badge_{member['member_number']}.png",
                    mimetype='image/png')

@app.route('/badge/download-pdf/<int:member_id>')
def download_pdf_badge(member_id):
    """Download member badge as PDF"""
    member = get_member(member_id)
    if not member:
        flash('Member not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        pdf_path, pdf_filename = BadgeGenerator.generate_pdf_badge(member)
        return send_file(pdf_path,
                        as_attachment=True,
                        download_name=f"badge_{member['member_number']}.pdf",
                        mimetype='application/pdf')
    except Exception as e:
        logger.error(f"Error generating PDF badge: {e}")
        flash('Error generating PDF badge.', 'danger')
        return redirect(url_for('view_badge', member_id=member_id))

@app.route('/badge/regenerate/<int:member_id>')
def regenerate_badge(member_id):
    """Regenerate member badge"""
    member = get_member(member_id)
    if not member:
        flash('Member not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Delete old badge
        if member.get('badge_image'):
            old_badge_path = os.path.join(Config.BADGE_FOLDER, member['badge_image'])
            if os.path.exists(old_badge_path):
                os.remove(old_badge_path)
        
        # Generate new badge
        badge_path, badge_filename = BadgeGenerator.generate_badge(member)
        update_member(member_id, {'badge_image': badge_filename})
        
        flash('Badge regenerated successfully!', 'success')
    except Exception as e:
        logger.error(f"Error regenerating badge: {e}")
        flash('Error regenerating badge.', 'danger')
    
    return redirect(url_for('view_badge', member_id=member_id))

@app.route('/verify-qr', methods=['GET', 'POST'])
def verify_qr():
    """Verify member by QR code"""
    form = QRVerificationForm()
    member = None
    error = None
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            qr_data = form.qr_data.data.strip()
            
            # Try to parse QR data
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

@app.route('/health')
def health_check():
    """Health check endpoint for deployment"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'group': Config.GROUP_NAME
    })

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
