"""
Professional badge generation module with security features
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
import os
import logging
import math
from datetime import datetime, timezone, timedelta
from config import Config
from .qr_generator import QRGenerator

logger = logging.getLogger(__name__)

class BadgeGenerator:
    """Professional ID badge generator with security features"""
    
    @staticmethod
    def generate_badge(member_data, include_bleed=False, watermark=True):
        """
        Generate professional ID badge with security features
        """
        try:
            width = Config.BADGE_WIDTH
            height = Config.BADGE_HEIGHT
            
            if include_bleed:
                bleed = Config.BLEED_SIZE
                width += bleed * 2
                height += bleed * 2
            
            # ============================================================
            # BACKGROUND: VIBRANT RED (highly visible from a distance)
            # ============================================================
            bg_color = (200, 0, 0)  # Vibrant Red
            accent_color = (255, 255, 255)  # White for text
            text_color = (255, 255, 255)  # White
            secondary_color = (160, 0, 0)  # Darker Red
            security_color = (130, 0, 0)  # Security element color
            
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # ============================================================
            # SECURITY FEATURE 1: GUILLOCHE PATTERN (background)
            # ============================================================
            for x in range(0, width, 12):
                for y in range(0, height, 12):
                    if (x + y) % 24 < 12:
                        draw.point((x, y), fill=(220, 50, 50))
                    else:
                        draw.point((x, y), fill=(180, 20, 20))
            
            # ============================================================
            # SECURITY FEATURE 2: MICROTEXT PATTERN
            # ============================================================
            try:
                micro_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 7)
            except:
                micro_font = ImageFont.load_default()
            
            microtext = "BBS BUSIA BODABODA SACCO • MEMBER ID • " * 20
            for i in range(0, height, 18):
                draw.text((5, i), microtext[:width//10], fill=(150, 20, 20, 80), font=micro_font)
            
            # ============================================================
            # SECURITY FEATURE 3: HOLOGRAPHIC BORDER
            # ============================================================
            holographic_colors = [(255, 215, 0), (200, 170, 0), (150, 130, 0)]
            for i in range(0, 20, 2):
                color_idx = i % len(holographic_colors)
                draw.rectangle([(i, i), (width - i, height - i)], 
                             outline=holographic_colors[color_idx], width=1)
            
            # Main border - Professional security border
            draw.rectangle([(8, 8), (width - 8, height - 8)], 
                         outline=(255, 255, 255), width=4)
            draw.rectangle([(14, 14), (width - 14, height - 14)], 
                         outline=secondary_color, width=2)
            
            # Corner ornaments (security feature)
            corner_size = 30
            for x, y in [(8, 8), (width - 8, 8), (8, height - 8), (width - 8, height - 8)]:
                draw.arc([(x - corner_size, y - corner_size), (x + corner_size, y + corner_size)], 
                         start=0, end=90, fill=(255, 255, 255), width=3)
            
            # ============================================================
            # LOAD FONTS - MAXIMUM SIZES FOR READABILITY
            # ============================================================
            try:
                # Largest: Member Number (increased ~100%)
                member_number_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 72)
                # Second Largest: Full Name (increased ~100%)
                name_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 54)
                # Medium: Labels
                label_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 32)
                # Values
                value_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 32)
                # Small: Footer
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 20)
                # Header fonts
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 38)
                header_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 30)
                logo_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 22)
                micro_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 7)
            except:
                member_number_font = ImageFont.load_default()
                name_font = ImageFont.load_default()
                label_font = ImageFont.load_default()
                value_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
                title_font = ImageFont.load_default()
                header_font = ImageFont.load_default()
                logo_font = ImageFont.load_default()
                micro_font = ImageFont.load_default()
            
            offset_x = bleed if include_bleed else 0
            offset_y = bleed if include_bleed else 0
            
            # ============================================================
            # HEADER - DARK RED WITH WHITE/GOLD ACCENTS
            # ============================================================
            header_height = 115
            for i in range(header_height):
                color = tuple([int((120, 0, 0)[j] * (1 - i/header_height) + (160, 10, 10)[j] * (i/header_height)) for j in range(3)])
                draw.rectangle([(offset_x + 12, offset_y + 12 + i), 
                               (width - offset_x - 12, offset_y + 12 + i + 1)], fill=color)
            
            # Header bottom accent line
            draw.rectangle([(offset_x + 12, offset_y + 12 + header_height), 
                           (width - offset_x - 12, offset_y + 12 + header_height + 3)], 
                         fill=(255, 215, 0))
            
            # ============================================================
            # SECURITY FEATURE 4: HOLOGRAM STRIP IN HEADER
            # ============================================================
            for i in range(0, 80, 12):
                draw.rectangle([(offset_x + 40 + i, offset_y + 18), 
                               (offset_x + 55 + i, offset_y + 22)], 
                              fill=(255, 255, 200, 60))
            
            # ============================================================
            # 4 LOGOS AT TOP RIGHT - PRESERVED
            # ============================================================
            logo_size = 55
            spacing = 8
            logos_start_x = width - offset_x - (logo_size * 4 + spacing * 3) - 25
            logos_start_y = offset_y + 18
            
            logo_files = [
                'sacco_logo.png',
                'county_logo.png',
                'national_logo.png',
                'partner_logo.png'
            ]
            
            for i, logo_file in enumerate(logo_files):
                try:
                    logo_path = os.path.join('static', 'images', logo_file)
                    if os.path.exists(logo_path):
                        logo = Image.open(logo_path)
                        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
                        if logo.mode != 'RGBA':
                            logo = logo.convert('RGBA')
                        x_pos = logos_start_x + i * (logo_size + spacing)
                        img.paste(logo, (x_pos, logos_start_y), logo)
                    else:
                        x_pos = logos_start_x + i * (logo_size + spacing)
                        draw.rectangle([(x_pos, logos_start_y), (x_pos + logo_size, logos_start_y + logo_size)], 
                                     outline=(255, 255, 255), width=2)
                        draw.text((x_pos + logo_size//2, logos_start_y + logo_size//2), 
                                 f"Logo{i+1}", fill=(255, 255, 255), font=small_font, anchor='mm')
                except Exception as e:
                    logger.warning(f"Could not load logo {logo_file}: {e}")
            
            # ============================================================
            # HEADER TEXT - PROFESSIONAL TYPOGRAPHY with official name
            # ============================================================
            draw.text((offset_x + 30, offset_y + 22), "BBS", 
                     fill=(255, 255, 255), font=title_font, anchor='lt')
            draw.text((offset_x + 30, offset_y + 58), "BUSIA BODABODA SACCO", 
                     fill=(255, 215, 0), font=header_font, anchor='lt')
            
            # ============================================================
            # LEFT COLUMN: PASSPORT PHOTO (TOP) + QR CODE (BOTTOM)
            # ============================================================
            
            # --- PASSPORT PHOTO SECTION (with orientation fix) ---
            photo_available = False
            if member_data.get('passport_photo'):
                photo_path = os.path.join(Config.UPLOAD_FOLDER, member_data['passport_photo'])
                if os.path.exists(photo_path):
                    try:
                        photo = Image.open(photo_path)
                        # Normalize orientation using EXIF
                        from .image_processor import ImageProcessor
                        photo = ImageProcessor.normalize_orientation(photo)
                        
                        # Target dimensions for rectangular photo
                        target_width = 240
                        target_height = 280
                        
                        # Preserve aspect ratio (no squishing)
                        photo_aspect = photo.width / photo.height
                        target_aspect = target_width / target_height
                        
                        if photo_aspect > target_aspect:
                            new_height = target_height
                            new_width = int(target_height * photo_aspect)
                        else:
                            new_width = target_width
                            new_height = int(target_width / photo_aspect)
                        
                        photo = photo.resize((new_width, new_height), Image.LANCZOS)
                        
                        if new_width > target_width:
                            left = (new_width - target_width) // 2
                            right = left + target_width
                            photo = photo.crop((left, 0, right, target_height))
                        elif new_height > target_height:
                            top = (new_height - target_height) // 2
                            bottom = top + target_height
                            photo = photo.crop((0, top, target_width, bottom))
                        
                        # Position (left side, top area)
                        photo_x = offset_x + 35
                        photo_y = offset_y + 135
                        
                        # Create rounded rectangle mask
                        mask = Image.new('L', (target_width, target_height), 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.rounded_rectangle([(0, 0), (target_width, target_height)], 
                                                    radius=12, fill=255)
                        
                        # Create shadow layer
                        shadow = Image.new('RGBA', (target_width + 12, target_height + 12), (0, 0, 0, 0))
                        shadow_draw = ImageDraw.Draw(shadow)
                        shadow_draw.rounded_rectangle([(4, 4), (target_width + 8, target_height + 8)], 
                                                      radius=14, fill=(0, 0, 0, 60))
                        img.paste(shadow, (photo_x - 6, photo_y - 6), shadow)
                        
                        # Paste photo
                        img.paste(photo, (photo_x, photo_y), mask)
                        photo_available = True
                        
                        # Professional double border
                        draw.rounded_rectangle([(photo_x - 4, photo_y - 4), 
                                               (photo_x + target_width + 4, photo_y + target_height + 4)], 
                                             radius=14, outline=(255, 255, 255), width=3)
                        draw.rounded_rectangle([(photo_x - 8, photo_y - 8), 
                                               (photo_x + target_width + 8, photo_y + target_height + 8)], 
                                             radius=16, outline=(200, 0, 0), width=1)
                    except Exception as e:
                        logger.error(f"Error loading photo: {e}")
            
            if not photo_available:
                # Professional placeholder
                draw.rounded_rectangle([(offset_x + 35, offset_y + 135), 
                                       (offset_x + 275, offset_y + 415)], 
                                     radius=12, outline=(255, 255, 255), width=3)
                draw.text((offset_x + 155, offset_y + 275), "PHOTO", fill=(255, 255, 255), 
                         font=value_font, anchor='mm')
            
            # --- QR CODE SECTION (Below Photo) - INCREASED 25% ---
            qr_path, qr_filename = QRGenerator.generate_qr(member_data, include_photo=True)
            if os.path.exists(qr_path):
                try:
                    qr_img = Image.open(qr_path)
                    # Increased QR size by 25% (from 180 to 225)
                    qr_size = 225
                    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
                    
                    # Position: Directly below passport photo
                    qr_x = offset_x + 42
                    qr_y = offset_y + 420
                    
                    # QR quiet zone (white margin)
                    draw.rectangle([(qr_x - 15, qr_y - 15), 
                                   (qr_x + qr_size + 15, qr_y + qr_size + 15)], 
                                 fill=(200, 0, 0))
                    
                    # Professional QR border
                    draw.rectangle([(qr_x - 10, qr_y - 10), 
                                   (qr_x + qr_size + 10, qr_y + qr_size + 10)], 
                                 outline=(255, 255, 255), width=3)
                    draw.rectangle([(qr_x - 14, qr_y - 14), 
                                   (qr_x + qr_size + 14, qr_y + qr_size + 14)], 
                                 outline=(160, 0, 0), width=1)
                    
                    # Paste QR
                    img.paste(qr_img, (qr_x, qr_y))
                    
                    # "SCAN TO VERIFY" caption
                    draw.text((qr_x + qr_size//2, qr_y + qr_size + 22), "SCAN TO VERIFY", 
                             fill=(255, 255, 255), font=small_font, anchor='mt')
                except Exception as e:
                    logger.error(f"Error placing QR code: {e}")
            
            # ============================================================
            # RIGHT COLUMN: MEMBER INFORMATION (MAXIMUM FONT SIZES)
            # ============================================================
            x_start = offset_x + 330
            y_start = offset_y + 135
            line_height = 48
            
            # Member Number (LARGEST)
            draw.text((x_start, y_start), "MEMBER NUMBER", fill=(255, 255, 255), font=label_font)
            draw.text((x_start + 260, y_start), member_data.get('member_number', 'N/A'), 
                     fill=(255, 255, 255), font=member_number_font)
            
            # Full Name (SECOND LARGEST)
            y_pos = y_start + 60
            draw.text((x_start, y_pos), "FULL NAME", fill=(255, 255, 255), font=label_font)
            draw.text((x_start + 260, y_pos), member_data.get('full_name', 'N/A'), 
                     fill=(255, 255, 255), font=name_font)
            
            # Remaining details with consistent spacing
            details = [
                ("NATIONAL ID", member_data.get('national_id', 'N/A')),
                ("TELEPHONE", member_data.get('telephone', 'N/A')),
                ("MOTORCYCLE", member_data.get('motorcycle_registration', 'N/A')),
                ("GROUP/STAGE", member_data.get('group_stage_name', 'N/A')),
                ("CHAIRMAN", member_data.get('chairman_name', 'N/A')),
                ("CHAIRMAN PHONE", member_data.get('chairman_phone', 'N/A'))
            ]
            
            y_pos = y_start + 110
            for label, value in details:
                draw.text((x_start, y_pos), label, fill=(255, 215, 0), font=label_font)
                draw.text((x_start + 260, y_pos), value if value else 'N/A', 
                         fill=(255, 255, 255), font=value_font)
                y_pos += line_height
            
            # ============================================================
            # FOOTER - ISSUE DATE, EXPIRY (5 years from issue), SERIAL
            # ============================================================
            # Get issue date - use stored date_registered or current time
            issue_date_str = member_data.get('date_registered')
            if issue_date_str:
                try:
                    if isinstance(issue_date_str, datetime):
                        issue_dt = issue_date_str
                    else:
                        issue_dt = datetime.strptime(issue_date_str, '%Y-%m-%d')
                except:
                    issue_dt = datetime.now(timezone.utc)
            else:
                issue_dt = datetime.now(timezone.utc)
            
            # If issue_dt is naive, make it aware
            if issue_dt.tzinfo is None:
                issue_dt = issue_dt.replace(tzinfo=timezone.utc)
            
            # Expiry date: exactly 5 years after issue date
            expiry_dt = issue_dt.replace(year=issue_dt.year + 5)
            
            issue_date = issue_dt.strftime('%Y-%m-%d')
            expiry_date = expiry_dt.strftime('%Y-%m-%d')
            
            # Footer section (bottom of right column)
            footer_y_start = height - offset_y - 105
            
            # Footer divider
            draw.rectangle([(x_start, footer_y_start - 12), (width - offset_x - 30, footer_y_start - 8)], 
                         fill=(255, 215, 0))
            
            # Date Issued
            draw.text((x_start, footer_y_start), f"Issued: {issue_date}", 
                     fill=(255, 255, 255), font=small_font)
            
            # Expiry (5 years from issue)
            draw.text((x_start + 260, footer_y_start), f"Expires: {expiry_date}", 
                     fill=(255, 255, 255), font=small_font)
            
            # Serial Number (security feature)
            serial = f"BBS-{member_data.get('member_number', '0000')}-{issue_dt.year}"
            draw.text((x_start, footer_y_start + 32), f"Serial: {serial}", 
                     fill=(255, 255, 255), font=small_font)
            
            # Group Name with official name
            draw.text((x_start + 260, footer_y_start + 32), "BBS (Busia Bodaboda SACCO)", 
                     fill=(255, 255, 255), font=small_font)
            
            # ============================================================
            # SECURITY FEATURE 5: VOID PATTERN
            # ============================================================
            void_text = "VOID" * 8
            draw.text((width - 200, height - 85), void_text, 
                     fill=(100, 20, 20, 30), font=header_font, angle=45)
            
            # ============================================================
            # SECURITY FEATURE 6: WATERMARK (diagonal text)
            # ============================================================
            if watermark and Config.SHOW_WATERMARK:
                watermark_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
                watermark_draw = ImageDraw.Draw(watermark_img)
                watermark_text = "BBS BUSIA BODABODA SACCO"
                for i in range(-height, height, 130):
                    watermark_draw.text((i, i), watermark_text, 
                                      fill=(255, 255, 255, 15),
                                      font=header_font, angle=35)
                # "ORIGINAL" watermark
                watermark_draw.text((width//2 - 80, height//2 + 20), "ORIGINAL", 
                                   fill=(255, 255, 255, 12), font=title_font, anchor='mm')
                img = Image.alpha_composite(img.convert('RGBA'), watermark_img).convert('RGB')
            
            # ============================================================
            # SECURITY FEATURE 7: GUARD BANDS
            # ============================================================
            band_colors = [(200, 0, 0), (255, 255, 255), (200, 0, 0)]
            for i, color in enumerate(band_colors):
                y_pos = height - offset_y - 55 + (i * 5)
                draw.rectangle([(offset_x + 20, y_pos), (offset_x + 180, y_pos + 3)], 
                             fill=color)
            
            # ============================================================
            # CROP MARKS (for professional printing)
            # ============================================================
            if include_bleed:
                crop_color = (255, 255, 255)
                mark_length = 18
                # Top-left
                draw.line([(offset_x + 10, offset_y), (offset_x + 10 + mark_length, offset_y)], 
                         fill=crop_color, width=1)
                draw.line([(offset_x, offset_y + 10), (offset_x, offset_y + 10 + mark_length)], 
                         fill=crop_color, width=1)
                # Top-right
                draw.line([(width - offset_x - 10, offset_y), (width - offset_x - 10 - mark_length, offset_y)], 
                         fill=crop_color, width=1)
                draw.line([(width - offset_x, offset_y + 10), (width - offset_x, offset_y + 10 + mark_length)], 
                         fill=crop_color, width=1)
                # Bottom-left
                draw.line([(offset_x + 10, height - offset_y), (offset_x + 10 + mark_length, height - offset_y)], 
                         fill=crop_color, width=1)
                draw.line([(offset_x, height - offset_y - 10), (offset_x, height - offset_y - 10 + mark_length)], 
                         fill=crop_color, width=1)
                # Bottom-right
                draw.line([(width - offset_x - 10, height - offset_y), (width - offset_x - 10 - mark_length, height - offset_y)], 
                         fill=crop_color, width=1)
                draw.line([(width - offset_x, height - offset_y - 10), (width - offset_x, height - offset_y - 10 + mark_length)], 
                         fill=crop_color, width=1)
            
            # ============================================================
            # SAVE BADGE
            # ============================================================
            filename = f"badge_{member_data['member_number']}.png"
            filepath = os.path.join(Config.BADGE_FOLDER, filename)
            img.save(filepath, 'PNG', quality=95, dpi=(Config.BADGE_DPI, Config.BADGE_DPI))
            
            logger.info(f"Security badge generated for member: {member_data['member_number']}")
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
            
            if include_bleed:
                page_size = landscape(A6)
                bleed_margin = 18
                page_width = page_size[0] + bleed_margin * 2
                page_height = page_size[1] + bleed_margin * 2
                page_size = (page_width, page_height)
            else:
                page_size = landscape(A6)
            
            c = canvas.Canvas(filepath, pagesize=page_size)
            
            badge_filename = f"badge_{member_data['member_number']}.png"
            badge_path = os.path.join(Config.BADGE_FOLDER, badge_filename)
            
            if os.path.exists(badge_path):
                img = ImageReader(badge_path)
                if include_bleed:
                    img_width = page_size[0] - 36
                    img_height = page_size[1] - 36
                    x = (page_size[0] - img_width) / 2
                    y = (page_size[1] - img_height) / 2
                    c.drawImage(img, x, y, width=img_width, height=img_height)
                else:
                    c.drawImage(img, 0, 0, width=page_size[0], height=page_size[1])
            
            now = datetime.now(timezone.utc)
            c.setFont("Helvetica", 8)
            c.setFillColorRGB(0.5, 0.5, 0.5)
            c.drawString(10, 10, f"Printed: {now.strftime('%Y-%m-%d %H:%M')}")
            c.drawString(10, 5, f"Member: {member_data['member_number']}")
            
            c.save()
            logger.info(f"PDF badge generated for member: {member_data['member_number']}")
            return filepath, filename
            
        except Exception as e:
            logger.error(f"Error generating PDF badge: {e}")
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
                logger.info(f"Batch badge generated for: {member['member_number']}")
            except Exception as e:
                results[member['member_number']] = {
                    'success': False,
                    'error': str(e)
                }
                logger.error(f"Failed to generate badge for {member['member_number']}: {e}")
        return results
