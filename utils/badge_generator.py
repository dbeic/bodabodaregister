"""
Professional badge generation module with security features
"""
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps
import os
import logging
from datetime import datetime
from config import Config
from .qr_generator import QRGenerator

logger = logging.getLogger(__name__)

class BadgeGenerator:
    """Professional ID badge generator"""
    
    @staticmethod
    def generate_badge(member_data, include_bleed=False, watermark=True):
        try:
            width = Config.BADGE_WIDTH
            height = Config.BADGE_HEIGHT
            
            if include_bleed:
                bleed = Config.BLEED_SIZE
                width += bleed * 2
                height += bleed * 2
            
            # Background - Vibrant Red
            bg_color = (200, 0, 0)
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Font loading with fallback
            try:
                font_large = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 48)
                font_medium = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 32)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 22)
            except:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            offset_x = bleed if include_bleed else 0
            offset_y = bleed if include_bleed else 0
            
            # === HEADER ===
            header_height = 100
            for i in range(header_height):
                color = tuple([int((140, 0, 0)[j] * (1 - i/header_height) + (180, 20, 20)[j] * (i/header_height)) for j in range(3)])
                draw.rectangle([(offset_x + 10, offset_y + 10 + i), 
                               (width - offset_x - 10, offset_y + 10 + i + 1)], fill=color)
            
            draw.rectangle([(offset_x + 10, offset_y + 10 + header_height), 
                           (width - offset_x - 10, offset_y + 10 + header_height + 4)], 
                         fill=(255, 215, 0))
            
            # Header text
            draw.text((offset_x + 30, offset_y + 18), "BODABODA", 
                     fill=(255, 255, 255), font=font_large, anchor='lt')
            draw.text((offset_x + 30, offset_y + 60), "IDENTIFICATION CARD", 
                     fill=(255, 215, 0), font=font_medium, anchor='lt')
            
            # === LOGOS ===
            logo_size = 50
            logos_start_x = width - offset_x - (logo_size * 4 + 8 * 3) - 25
            logos_start_y = offset_y + 15
            
            logo_files = ['sacco_logo.png', 'county_logo.png', 'national_logo.png', 'partner_logo.png']
            for i, logo_file in enumerate(logo_files):
                try:
                    logo_path = os.path.join('static', 'images', logo_file)
                    if os.path.exists(logo_path):
                        logo = Image.open(logo_path)
                        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
                        if logo.mode != 'RGBA':
                            logo = logo.convert('RGBA')
                        x_pos = logos_start_x + i * (logo_size + 8)
                        img.paste(logo, (x_pos, logos_start_y), logo)
                except:
                    pass
            
            # === PASSPORT PHOTO ===
            photo_available = False
            if member_data.get('passport_photo'):
                photo_path = os.path.join(Config.UPLOAD_FOLDER, member_data['passport_photo'])
                if os.path.exists(photo_path):
                    try:
                        photo = Image.open(photo_path)
                        photo = photo.resize((230, 270), Image.LANCZOS)
                        photo_x = offset_x + 30
                        photo_y = offset_y + 130
                        
                        mask = Image.new('L', (230, 270), 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.rounded_rectangle([(0, 0), (230, 270)], radius=10, fill=255)
                        
                        img.paste(photo, (photo_x, photo_y), mask)
                        photo_available = True
                        
                        draw.rounded_rectangle([(photo_x - 3, photo_y - 3), 
                                               (photo_x + 233, photo_y + 273)], 
                                             radius=12, outline=(255, 255, 255), width=3)
                    except Exception as e:
                        logger.error(f"Photo error: {e}")
            
            if not photo_available:
                draw.rounded_rectangle([(offset_x + 30, offset_y + 130), 
                                       (offset_x + 260, offset_y + 400)], 
                                     radius=10, outline=(255, 255, 255), width=2)
                draw.text((offset_x + 145, offset_y + 265), "PHOTO", fill=(255, 255, 255), 
                         font=font_medium, anchor='mm')
            
            # === QR CODE ===
            qr_path, qr_filename = QRGenerator.generate_qr(member_data)
            if os.path.exists(qr_path):
                try:
                    qr_img = Image.open(qr_path)
                    qr_size = 200
                    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
                    qr_x = offset_x + 45
                    qr_y = offset_y + 410
                    
                    draw.rectangle([(qr_x - 10, qr_y - 10), 
                                   (qr_x + qr_size + 10, qr_y + qr_size + 10)], 
                                 outline=(255, 255, 255), width=2)
                    img.paste(qr_img, (qr_x, qr_y))
                    draw.text((qr_x + qr_size//2, qr_y + qr_size + 18), "SCAN TO VERIFY", 
                             fill=(255, 255, 255), font=font_small, anchor='mt')
                except Exception as e:
                    logger.error(f"QR error: {e}")
            
            # === MEMBER INFORMATION ===
            x_start = offset_x + 290
            y_start = offset_y + 130
            line_height = 42
            
            # Member Number
            draw.text((x_start, y_start), "MEMBER NUMBER:", fill=(255, 215, 0), font=font_medium)
            draw.text((x_start + 240, y_start), member_data.get('member_number', 'N/A'), 
                     fill=(255, 255, 255), font=font_large)
            
            # Full Name
            y_pos = y_start + 50
            draw.text((x_start, y_pos), "FULL NAME:", fill=(255, 215, 0), font=font_medium)
            draw.text((x_start + 240, y_pos), member_data.get('full_name', 'N/A'), 
                     fill=(255, 255, 255), font=font_medium)
            
            # Other details
            details = [
                ("NATIONAL ID:", member_data.get('national_id', 'N/A')),
                ("TELEPHONE:", member_data.get('telephone', 'N/A')),
                ("MOTORCYCLE:", member_data.get('motorcycle_registration', 'N/A')),
                ("GROUP/STAGE:", member_data.get('group_stage_name', 'N/A'))
            ]
            
            y_pos = y_start + 95
            for label, value in details:
                draw.text((x_start, y_pos), label, fill=(255, 215, 0), font=font_small)
                draw.text((x_start + 240, y_pos), value if value else 'N/A', 
                         fill=(255, 255, 255), font=font_small)
                y_pos += line_height
            
            # Chairman
            y_pos += 5
            draw.text((x_start, y_pos), "CHAIRMAN:", fill=(255, 215, 0), font=font_small)
            draw.text((x_start + 240, y_pos), member_data.get('chairman_name', 'N/A'), 
                     fill=(255, 255, 255), font=font_small)
            
            y_pos += line_height
            draw.text((x_start, y_pos), "CHAIRMAN PHONE:", fill=(255, 215, 0), font=font_small)
            draw.text((x_start + 240, y_pos), member_data.get('chairman_phone', 'N/A'), 
                     fill=(255, 255, 255), font=font_small)
            
            # === FOOTER ===
            issue_date = member_data.get('date_registered', datetime.now().strftime('%Y-%m-%d'))
            if isinstance(issue_date, datetime):
                issue_date = issue_date.strftime('%Y-%m-%d')
            
            footer_y = height - offset_y - 75
            draw.rectangle([(x_start, footer_y), (width - offset_x - 30, footer_y + 3)], 
                         fill=(255, 215, 0))
            
            draw.text((x_start, footer_y + 12), f"Issued: {issue_date}", 
                     fill=(255, 255, 255), font=font_small)
            
            serial = f"BSB-{member_data.get('member_number', '0000')}"
            draw.text((x_start + 250, footer_y + 12), f"Serial: {serial}", 
                     fill=(255, 255, 255), font=font_small)
            
            draw.text((x_start, footer_y + 38), Config.GROUP_NAME, 
                     fill=(255, 215, 0), font=font_small)
            
            # === SAVE ===
            filename = f"badge_{member_data['member_number']}.png"
            filepath = os.path.join(Config.BADGE_FOLDER, filename)
            img.save(filepath, 'PNG', quality=95)
            
            logger.info(f"Badge generated for member: {member_data['member_number']}")
            return filepath, filename
            
        except Exception as e:
            logger.error(f"Error generating badge: {e}")
            raise
    
    @staticmethod
    def generate_pdf_badge(member_data, include_bleed=False):
        try:
            from reportlab.lib.pagesizes import landscape, A6
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
            import os
            
            filename = f"badge_{member_data['member_number']}.pdf"
            filepath = os.path.join(Config.EXPORT_FOLDER, filename)
            c = canvas.Canvas(filepath, pagesize=landscape(A6))
            
            badge_filename = f"badge_{member_data['member_number']}.png"
            badge_path = os.path.join(Config.BADGE_FOLDER, badge_filename)
            
            if os.path.exists(badge_path):
                img = ImageReader(badge_path)
                c.drawImage(img, 0, 0, width=landscape(A6)[0], height=landscape(A6)[1])
            
            c.save()
            return filepath, filename
            
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            raise
    
    @staticmethod
    def generate_batch_badges(members, include_bleed=False):
        results = {}
        for member in members:
            try:
                badge_path, badge_filename = BadgeGenerator.generate_badge(member, include_bleed)
                results[member['member_number']] = {
                    'success': True,
                    'path': badge_path,
                    'filename': badge_filename
                }
            except Exception as e:
                results[member['member_number']] = {
                    'success': False,
                    'error': str(e)
                }
        return results
