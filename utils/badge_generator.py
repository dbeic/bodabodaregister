"""
Professional badge generation module
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import logging
from datetime import datetime
from config import Config
from .qr_generator import QRGenerator

logger = logging.getLogger(__name__)

class BadgeGenerator:
    """Professional ID badge generator"""
    
    @staticmethod
    def generate_badge(member_data):
        """
        Generate professional ID badge
        
        Args:
            member_data: Dictionary containing member information
        
        Returns:
            tuple: (filepath, filename)
        """
        try:
            # Create badge image
            width = Config.BADGE_WIDTH
            height = Config.BADGE_HEIGHT
            img = Image.new('RGB', (width, height), Config.BADGE_BG_COLOR)
            draw = ImageDraw.Draw(img)
            
            # Colors
            bg_color = Config.BADGE_BG_COLOR
            accent_color = Config.BADGE_ACCENT_COLOR
            text_color = Config.BADGE_TEXT_COLOR
            
            # Load fonts (using default fonts, can be customized)
            try:
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 28)
                header_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 22)
                label_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 16)
                value_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 16)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 12)
            except:
                # Fallback to default font
                title_font = ImageFont.load_default()
                header_font = ImageFont.load_default()
                label_font = ImageFont.load_default()
                value_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            # Draw header background
            draw.rectangle([(0, 0), (width, 80)], fill=accent_color)
            
            # Draw header text
            header_text = Config.GROUP_NAME.upper()
            draw.text((width//2, 20), "BODABODA MEMBER IDENTIFICATION CARD", 
                     fill=text_color, font=title_font, anchor='mt')
            
            # Draw gold accent line
            draw.rectangle([(0, 80), (width, 85)], fill=accent_color)
            
            # Draw border
            draw.rectangle([(5, 5), (width-5, height-5)], outline=accent_color, width=3)
            
            # Load and place passport photo
            if member_data.get('passport_photo'):
                photo_path = os.path.join(Config.UPLOAD_FOLDER, member_data['passport_photo'])
                if os.path.exists(photo_path):
                    try:
                        photo = Image.open(photo_path)
                        photo = photo.resize((220, 280), Image.LANCZOS)
                        
                        # Create circular mask for photo
                        mask = Image.new('L', (220, 280), 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse([(0, 0), (220, 280)], fill=255)
                        
                        # Apply mask
                        img.paste(photo, (30, 120), mask)
                        
                        # Draw photo border
                        draw.ellipse([(30, 120), (250, 400)], outline=accent_color, width=3)
                    except Exception as e:
                        logger.error(f"Error loading photo: {e}")
            
            # Draw member details on right side
            x_start = 280
            y_start = 120
            line_height = 30
            
            details = [
                ("Member Number:", member_data['member_number']),
                ("Full Name:", member_data['full_name']),
                ("National ID:", member_data['national_id']),
                ("Telephone:", member_data['telephone']),
                ("Motorcycle Reg:", member_data.get('motorcycle_registration', 'N/A')),
                ("Group/Stage:", member_data.get('group_stage_name', 'N/A'))
            ]
            
            for i, (label, value) in enumerate(details):
                y_pos = y_start + (i * line_height)
                
                # Draw label
                draw.text((x_start, y_pos), label, fill=accent_color, font=label_font)
                
                # Draw value
                draw.text((x_start + 150, y_pos), value, fill=text_color, font=value_font)
            
            # Draw Chairman info
            y_pos = y_start + (len(details) * line_height) + 20
            draw.text((x_start, y_pos), "Chairman:", fill=accent_color, font=label_font)
            draw.text((x_start + 150, y_pos), member_data.get('chairman_name', 'N/A'), 
                     fill=text_color, font=value_font)
            
            # Draw Chairman Phone
            y_pos += line_height
            draw.text((x_start, y_pos), "Chairman Phone:", fill=accent_color, font=label_font)
            draw.text((x_start + 150, y_pos), member_data.get('chairman_phone', 'N/A'), 
                     fill=text_color, font=value_font)
            
            # Generate and place QR Code
            qr_path, qr_filename = QRGenerator.generate_qr(member_data)
            if os.path.exists(qr_path):
                try:
                    qr_img = Image.open(qr_path)
                    qr_img = qr_img.resize((160, 160), Image.LANCZOS)
                    qr_x = width - 190
                    qr_y = height - 190
                    img.paste(qr_img, (qr_x, qr_y))
                    
                    # Draw QR border
                    draw.rectangle([(qr_x - 5, qr_y - 5), (qr_x + 165, qr_y + 165)], 
                                 outline=accent_color, width=2)
                except Exception as e:
                    logger.error(f"Error placing QR code: {e}")
            
            # Draw issue date
            issue_date = member_data.get('date_registered', datetime.now().strftime('%Y-%m-%d'))
            if isinstance(issue_date, datetime):
                issue_date = issue_date.strftime('%Y-%m-%d')
            
            draw.text((width - 190, height - 30), f"Date Issued: {issue_date}", 
                     fill=text_color, font=small_font, anchor='rb')
            
            # Draw footer line
            draw.rectangle([(30, height - 35), (width - 210, height - 30)], fill=accent_color)
            
            # Draw group name in footer
            draw.text((30, height - 20), f"{Config.GROUP_NAME}", 
                     fill=accent_color, font=small_font)
            
            # Save badge
            filename = f"badge_{member_data['member_number']}.png"
            filepath = os.path.join(Config.BADGE_FOLDER, filename)
            img.save(filepath, 'PNG', quality=95)
            
            logger.info(f"Badge generated for member: {member_data['member_number']}")
            return filepath, filename
            
        except Exception as e:
            logger.error(f"Error generating badge: {e}")
            raise
    
    @staticmethod
    def generate_pdf_badge(member_data):
        """
        Generate PDF version of the badge
        
        Args:
            member_data: Dictionary containing member information
        
        Returns:
            str: Path to generated PDF file
        """
        try:
            from reportlab.lib.pagesizes import landscape, A6
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
            import os
            
            # Create PDF
            filename = f"badge_{member_data['member_number']}.pdf"
            filepath = os.path.join(Config.BADGE_FOLDER, filename)
            
            c = canvas.Canvas(filepath, pagesize=landscape(A6))
            
            # Get badge image
            badge_filename = f"badge_{member_data['member_number']}.png"
            badge_path = os.path.join(Config.BADGE_FOLDER, badge_filename)
            
            if os.path.exists(badge_path):
                img = ImageReader(badge_path)
                c.drawImage(img, 0, 0, width=landscape(A6)[0], height=landscape(A6)[1])
            
            c.save()
            logger.info(f"PDF badge generated for member: {member_data['member_number']}")
            return filepath, filename
            
        except Exception as e:
            logger.error(f"Error generating PDF badge: {e}")
            raise
