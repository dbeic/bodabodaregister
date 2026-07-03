"""
Bodaboda SACCO Member Registration and Badge Generation System
Complete Flask Application with PostgreSQL, QR Codes, and Professional Badges
"""
import os
import logging
import zipfile
import tempfile
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, HiddenField, SelectField, BooleanField
from wtforms.validators import DataRequired, Length, Regexp

from config import config, Config
from database import (
    db, create_member, get_member, get_member_by_number,
    get_member_by_national_id, get_member_by_telephone,
    get_all_members, get_members_count, update_member,
    delete_member, get_recent_members, search_members_by_qr,
    get_unissued_members, get_issued_members, log_badge_issuance,
    get_issuance_log
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

class BatchIssuanceForm(FlaskForm):
    """Batch badge issuance form"""
    format_type = SelectField('Print Format', choices=[('png', 'PNG'), ('pdf', 'PDF'), ('both', 'Both')])
    include_bleed = BooleanField('Include Bleed Area (for professional printing)')
    print_quality = SelectField('Print Quality', choices=[('draft', 'Draft'), ('standard', 'Standard'), ('high', 'High')])

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
                'badge_image': None,
                'badge_issued': False,
                'badge_issued_date': None,
                'badge_issued_by': None
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
            
            # Get the member data
            member = get_member(member_id)
            
            if member:
                # Generate badge
                try:
                    badge_path, badge_filename = BadgeGenerator.generate_badge(member, include_bleed=True)
                    # Update member with badge image
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
def dashboard():
    """Member dashboard with search and pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        filter_type = request.args.get('filter', 'all')
        per_page = 20
        offset = (page - 1) * per_page
        
        # Get members with filters
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
        
        # Get stats
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
            if updated_member:
                badge_path, badge_filename = BadgeGenerator.generate_badge(updated_member, include_bleed=True)
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
    
    # Get issuance log
    issuance_log = get_issuance_log(member_id, 10)
    
    return render_template('badge.html', member=member, issuance_log=issuance_log)

@app.route('/badge/download/<int:member_id>')
def download_badge(member_id):
    """Download member badge as PNG"""
    member = get_member(member_id)
    if not member:
        flash('Member not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    format_type = request.args.get('format', 'png')
    include_bleed = request.args.get('bleed', 'false').lower() == 'true'
    
    badge_filename = member.get('badge_image')
    if not badge_filename:
        # Generate badge if it doesn't exist
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
    
    # Log issuance
    if format_type == 'pdf':
        log_badge_issuance(member_id, 'system', format_type, 'high')
        # Generate PDF
        try:
            pdf_path, pdf_filename = BadgeGenerator.generate_pdf_badge(member, include_bleed=include_bleed)
            return send_file(pdf_path,
                           as_attachment=True,
                           download_name=f"badge_{member['member_number']}.pdf",
                           mimetype='application/pdf')
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            flash('Error generating PDF badge.', 'danger')
            return redirect(url_for('view_badge', member_id=member_id))
    
    # Log PNG issuance
    log_badge_issuance(member_id, 'system', 'png', 'high')
    update_member(member_id, {
        'badge_issued': True,
        'badge_issued_date': datetime.now(),
        'badge_issued_by': 'system',
        'badge_print_count': (member.get('badge_print_count', 0) + 1),
        'last_printed': datetime.now()
    })
    
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
    
    include_bleed = request.args.get('bleed', 'true').lower() == 'true'
    
    try:
        pdf_path, pdf_filename = BadgeGenerator.generate_pdf_badge(member, include_bleed=include_bleed)
        
        # Log issuance
        log_badge_issuance(member_id, 'system', 'pdf', 'high')
        update_member(member_id, {
            'badge_issued': True,
            'badge_issued_date': datetime.now(),
            'badge_issued_by': 'system',
            'badge_print_count': (member.get('badge_print_count', 0) + 1),
            'last_printed': datetime.now()
        })
        
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
        
        # Generate new badge with bleed
        badge_path, badge_filename = BadgeGenerator.generate_badge(member, include_bleed=True)
        update_member(member_id, {'badge_image': badge_filename})
        
        flash('Badge regenerated successfully!', 'success')
    except Exception as e:
        logger.error(f"Error regenerating badge: {e}")
        flash('Error regenerating badge.', 'danger')
    
    return redirect(url_for('view_badge', member_id=member_id))

@app.route('/badge/issue/<int:member_id>', methods=['POST'])
def issue_badge(member_id):
    """Manually issue a badge to a member"""
    member = get_member(member_id)
    if not member:
        return jsonify({'success': False, 'error': 'Member not found'}), 404
    
    try:
        update_member(member_id, {
            'badge_issued': True,
            'badge_issued_date': datetime.now(),
            'badge_issued_by': request.form.get('issued_by', 'system'),
            'badge_print_count': (member.get('badge_print_count', 0) + 1),
            'last_printed': datetime.now()
        })
        
        log_badge_issuance(
            member_id,
            request.form.get('issued_by', 'system'),
            request.form.get('format', 'standard'),
            request.form.get('quality', 'high'),
            request.form.get('notes', 'Manual issuance')
        )
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error issuing badge: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/badge/batch', methods=['GET', 'POST'])
def batch_badges():
    """Batch badge issuance and printing"""
    form = BatchIssuanceForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            members = get_unissued_members()
            if not members:
                flash('No unissued members found.', 'warning')
                return redirect(url_for('batch_badges'))
            
            format_type = form.format_type.data
            include_bleed = form.include_bleed.data
            print_quality = form.print_quality.data
            
            # Generate badges for all members
            results = BadgeGenerator.generate_batch_badges(members, include_bleed=include_bleed)
            
            # Log issuances
            for member in members:
                if results.get(member['member_number'], {}).get('success'):
                    log_badge_issuance(
                        member['id'],
                        'batch_system',
                        format_type,
                        print_quality,
                        f'Batch issuance on {datetime.now().strftime("%Y-%m-%d")}'
                    )
                    update_member(member['id'], {
                        'badge_issued': True,
                        'badge_issued_date': datetime.now(),
                        'badge_issued_by': 'batch_system',
                        'badge_print_count': (member.get('badge_print_count', 0) + 1),
                        'last_printed': datetime.now()
                    })
            
            success_count = sum(1 for r in results.values() if r.get('success'))
            flash(f'Successfully generated {success_count} badges out of {len(members)} members.', 'success')
            
            # Create ZIP download if requested
            if format_type in ['pdf', 'both']:
                zip_filename = f"badges_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
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
                
                return send_file(zip_path,
                               as_attachment=True,
                               download_name=zip_filename,
                               mimetype='application/zip')
            
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            flash('Error processing batch badges.', 'danger')
    
    unissued_count = len(get_unissued_members())
    issued_count = len(get_issued_members())
    
    return render_template('batch_badges.html', 
                         form=form,
                         unissued_count=unissued_count,
                         issued_count=issued_count)

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

@app.route('/export/members')
def export_members():
    """Export member data"""
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
            
            # Write header
            headers = ['Member Number', 'Full Name', 'National ID', 'Telephone', 
                      'Group', 'Chairman', 'Badge Issued', 'Date Registered']
            writer.writerow(headers)
            
            # Write data
            for m in members:
                writer.writerow([
                    m['member_number'], m['full_name'], m['national_id'],
                    m['telephone'], m['group_stage_name'], m['chairman_name'],
                    'Yes' if m.get('badge_issued') else 'No',
                    m.get('date_registered', '')
                ])
            
            output.seek(0)
            return send_file(
                StringIO(output.getvalue()),
                as_attachment=True,
                download_name=f"members_{datetime.now().strftime('%Y%m%d')}.csv",
                mimetype='text/csv'
            )
        
        flash(f'Export format {format_type} not supported yet.', 'warning')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        logger.error(f"Error exporting members: {e}")
        flash('Error exporting members.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/health')
def health_check():
    """Health check endpoint for deployment"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'group': Config.GROUP_NAME,
        'features': {
            'badge_generation': True,
            'qr_codes': True,
            'batch_issuance': True,
            'print_ready': True
        }
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
