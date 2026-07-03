"""
Award-Winning Professional Badge Generator - Print Ready
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
import os
import logging
from datetime import datetime
from config import Config
from .qr_generator import QRGenerator

logger = logging.getLogger(__name__)

class BadgeGenerator:
    """Professional ID badge generator with award-winning design"""
    
    @staticmethod
    def generate_badge(member_data, include_bleed=False, watermark=True):
        """
        Generate award-winning professional ID badge
        
        Args:
            member_data: Dictionary containing member information
            include_bleed: Whether to include bleed area for printing
            watermark: Whether to include watermark
        
        Returns:
            tuple: (filepath, filename)
        """
        try:
            # Create badge image with proper dimensions
            width = Config.BADGE_WIDTH
            height = Config.BADGE_HEIGHT
            
            if include_bleed:
                bleed = Config.BLEED_SIZE
                width += bleed * 2
                height += bleed * 2
            
            # ================================================================
            # RED BACKGROUND - Custom Colors
            # ================================================================
            RED_BG = (180, 20, 20)        # Rich red background
            RED_DARK = (120, 10, 10)       # Darker red for gradients
            GOLD_ACCENT = (212, 175, 55)   # Gold for accents
            WHITE_TEXT = (255, 255, 255)   # White text
            RED_LIGHT = (220, 50, 50)      # Lighter red for borders
            
            # Create base image with red gradient background
            img = Image.new('RGB', (width, height), RED_BG)
            draw = ImageDraw.Draw(img)
            
            # ================================================================
            # AWARD-WINNING FONT SIZES - DOUBLED FOR MAXIMUM READABILITY
            # ================================================================
            try:
                # Main title - Largest
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 72)
                # Subtitle
                header_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 48)
                # Labels (MEMBER NO:, NAME:, etc.)
                label_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 30)
                # Values (actual data)
                value_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 34)
                # Small text (footer, phone)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 24)
                # Logo/org name
                logo_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 32)
                # Member Number - Extra Large
                number_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 62)
                # Member Name - Very Large
                name_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 40)
                # Tiny text for QR label
                qr_label_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 20)
                # Logo text font
                logo_text_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 12)
            except:
                # Fallback to default if fonts not found
                title_font = ImageFont.load_default()
                header_font = ImageFont.load_default()
                label_font = ImageFont.load_default()
                value_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
                logo_font = ImageFont.load_default()
                number_font = ImageFont.load_default()
                name_font = ImageFont.load_default()
                qr_label_font = ImageFont.load_default()
                logo_text_font = ImageFont.load_default()
            
            offset_x = bleed if include_bleed else 0
            offset_y = bleed if include_bleed else 0
            
            # ================================================================
            # 1. GRADIENT HEADER - Red to Dark Red
            # ================================================================
            header_height = 160
            for i in range(header_height):
                ratio = i / header_height
                r = int(RED_BG[0] * (1 - ratio) + RED_DARK[0] * ratio)
                g = int(RED_BG[1] * (1 - ratio) + RED_DARK[1] * ratio)
                b = int(RED_BG[2] * (1 - ratio) + RED_DARK[2] * ratio)
                draw.rectangle([(offset_x, offset_y + i), (width - offset_x, offset_y + i + 1)], fill=(r, g, b))
            
            # ================================================================
            # 2. FOUR CUSTOMIZABLE SQUARE LOGOS - Top Right Empty Space
            # ================================================================
            logo_size = 70
            logo_spacing = 8
            logos_total_width = (logo_size * 4) + (logo_spacing * 3)
            logo_start_x = width - offset_x - logos_total_width - 30
            logo_y = offset_y + 20
            
            # Logo definitions with placeholder colors and labels
            logos = [
                {"name": "GOV", "color": (220, 220, 220), "label": "GOV"},
                {"name": "BUSIA", "color": (200, 200, 200), "label": "BUSIA"},
                {"name": "BAK", "color": (180, 180, 180), "label": "BAK"},
                {"name": "SACCO", "color": (160, 160, 160), "label": "SACCO"}
            ]
            
            for idx, logo_info in enumerate(logos):
                logo_x = logo_start_x + (idx * (logo_size + logo_spacing))
                
                # Draw square logo background with border
                draw.rectangle([(logo_x, logo_y), (logo_x + logo_size, logo_y + logo_size)], 
                             fill=logo_info["color"], outline=GOLD_ACCENT, width=2)
                
                # Draw logo label inside
                draw.text((logo_x + logo_size//2, logo_y + logo_size//2 - 6), 
                         logo_info["label"], fill=(50, 50, 50), font=logo_text_font, anchor='mm')
                
                # Draw small decorative line under logo text
                draw.line([(logo_x + 10, logo_y + logo_size - 15), 
                          (logo_x + logo_size - 10, logo_y + logo_size - 15)], 
                         fill=(50, 50, 50), width=1)
            
            # ================================================================
            # 3. HEADER TEXT - With Professional Shadow Effects
            # ================================================================
            # Shadow for "BODABODA"
            draw.text((width//2 + 4, offset_y + 36), "BODABODA", 
                     fill=(0, 0, 0, 80), font=title_font, anchor='mt')
            draw.text((width//2, offset_y + 32), "BODABODA", 
                     fill=WHITE_TEXT, font=title_font, anchor='mt')
            
            # Shadow for "MEMBER IDENTIFICATION CARD"
            draw.text((width//2 + 3, offset_y + 106), "MEMBER IDENTIFICATION CARD", 
                     fill=(0, 0, 0, 60), font=header_font, anchor='mt')
            draw.text((width//2, offset_y + 103), "MEMBER IDENTIFICATION CARD", 
                     fill=WHITE_TEXT, font=header_font, anchor='mt')
            
            # ================================================================
            # 4. DECORATIVE GOLD LINE - Premium Gradient Effect
            # ================================================================
            line_y = offset_y + header_height - 8
            line_width = width - offset_x * 2
            for i in range(line_width):
                ratio = i / line_width
                gold_shift = int((GOLD_ACCENT[0] - 160) * abs(ratio - 0.5) * 2)
                r = max(180, GOLD_ACCENT[0] - gold_shift)
                g = max(140, GOLD_ACCENT[1] - gold_shift)
                b = max(40, GOLD_ACCENT[2] - gold_shift)
                draw.rectangle([(offset_x + i, line_y), (offset_x + i + 1, line_y + 5)], fill=(r, g, b))
            
            # ================================================================
            # 5. PROFESSIONAL BORDERS - Triple Border System
            # ================================================================
            # Outer border - subtle dark red
            draw.rectangle([(offset_x + 10, offset_y + 10), (width - offset_x - 10, height - offset_y - 10)], 
                         outline=(100, 20, 20), width=2)
            # Middle border - Gold accent
            draw.rectangle([(offset_x + 16, offset_y + 16), (width - offset_x - 16, height - offset_y - 16)], 
                         outline=GOLD_ACCENT, width=3)
            # Inner border - subtle
            draw.rectangle([(offset_x + 22, offset_y + 22), (width - offset_x - 22, height - offset_y - 22)], 
                         outline=(150, 40, 40), width=1)
            
            # ================================================================
            # 6. PHOTO SECTION - Premium with Shadow and Rounded Corners
            # ================================================================
            photo_x = offset_x + 55
            photo_y = offset_y + 195
            photo_width = 280
            photo_height = 340
            
            # Photo shadow effect
            shadow_offset = 5
            draw.rounded_rectangle([(photo_x + shadow_offset, photo_y + shadow_offset), 
                                   (photo_x + photo_width + shadow_offset, photo_y + photo_height + shadow_offset)], 
                                 radius=16, fill=(0, 0, 0, 50))
            
            # Load and place photo - NO FORCED ROTATION
            photo_available = False
            if member_data.get('passport_photo'):
                photo_path = os.path.join(Config.UPLOAD_FOLDER, member_data['passport_photo'])
                if os.path.exists(photo_path):
                    try:
                        photo = Image.open(photo_path)
                        
                        # Auto-rotate based on EXIF - NO FORCED ROTATION
                        photo = ImageOps.exif_transpose(photo)
                        
                        # Resize to fit photo area (portrait)
                        photo = photo.resize((photo_width, photo_height), Image.LANCZOS)
                        photo_available = True
                        
                        # Create rounded rectangle mask
                        mask = Image.new('L', (photo_width, photo_height), 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.rounded_rectangle([(0, 0), (photo_width, photo_height)], radius=16, fill=255)
                        
                        # Apply mask
                        photo_with_mask = Image.new('RGBA', (photo_width, photo_height), (0, 0, 0, 0))
                        photo_with_mask.paste(photo, (0, 0))
                        photo_with_mask.putalpha(mask)
                        
                        # Paste photo
                        img.paste(photo_with_mask, (photo_x, photo_y), photo_with_mask)
                        
                        # Photo border - Gold with thickness
                        draw.rounded_rectangle([(photo_x - 2, photo_y - 2), 
                                               (photo_x + photo_width + 2, photo_y + photo_height + 2)], 
                                             radius=18, outline=GOLD_ACCENT, width=4)
                        draw.rounded_rectangle([(photo_x - 5, photo_y - 5), 
                                               (photo_x + photo_width + 5, photo_y + photo_height + 5)], 
                                             radius=20, outline=(150, 40, 40), width=1)
                    except Exception as e:
                        logger.error(f"Error loading photo: {e}")
            
            # Photo placeholder if no photo
            if not photo_available:
                draw.rounded_rectangle([(photo_x, photo_y), (photo_x + photo_width, photo_y + photo_height)], 
                                     radius=16, fill=(100, 20, 20), outline=GOLD_ACCENT, width=3)
                draw.text((photo_x + photo_width//2, photo_y + photo_height//2 - 20), 
                         "PHOTO", fill=(180, 180, 180), font=value_font, anchor='mm')
                draw.text((photo_x + photo_width//2, photo_y + photo_height//2 + 40), 
                         "UPLOAD", fill=(180, 180, 180), font=small_font, anchor='mm')
            
            # ================================================================
            # 7. MEMBER DETAILS - Large, Clear, Professional - NO OVERLAP
            # ================================================================
            # Start text after photo with proper spacing
            text_x = photo_x + photo_width + 55
            text_y = photo_y + 10
            
            # Member Number - Largest, Most Prominent
            draw.text((text_x, text_y), "MEMBER NO:", fill=GOLD_ACCENT, font=label_font)
            member_num = member_data.get('member_number', 'N/A')
            draw.text((text_x + 280, text_y - 4), member_num, fill=GOLD_ACCENT, font=number_font)
            
            # Separator line with spacing
            sep_y = text_y + 80
            draw.line([(text_x, sep_y), (width - offset_x - 55, sep_y)], fill=GOLD_ACCENT, width=2)
            
            # Full Name - Very Large and Bold - SPACED PROPERLY
            y_pos = sep_y + 45
            draw.text((text_x, y_pos), "FULL NAME", fill=GOLD_ACCENT, font=label_font)
            name_text = member_data.get('full_name', 'N/A')
            draw.text((text_x + 280, y_pos), name_text, fill=WHITE_TEXT, font=name_font)
            
            # ================================================================
            # 8. TWO-COLUMN DETAILS - Clean, Readable, NO OVERLAPS
            # ================================================================
            y_pos += 75
            col1_x = text_x
            col2_x = text_x + 280
            
            # Column 1: Labels (Left)
            label_y = y_pos
            
            # ID NUMBER
            draw.text((col1_x, label_y), "ID NUMBER", fill=GOLD_ACCENT, font=label_font)
            id_value = member_data.get('national_id', 'N/A')
            draw.text((col2_x, label_y), id_value, fill=WHITE_TEXT, font=value_font)
            label_y += 58
            
            # PHONE
            draw.text((col1_x, label_y), "PHONE", fill=GOLD_ACCENT, font=label_font)
            phone_value = member_data.get('telephone', 'N/A')
            draw.text((col2_x, label_y), phone_value, fill=WHITE_TEXT, font=value_font)
            label_y += 58
            
            # MOTORCYCLE
            draw.text((col1_x, label_y), "MOTORCYCLE", fill=GOLD_ACCENT, font=label_font)
            moto_value = member_data.get('motorcycle_registration', 'N/A')
            draw.text((col2_x, label_y), moto_value, fill=WHITE_TEXT, font=value_font)
            label_y += 58
            
            # GROUP/STAGE
            draw.text((col1_x, label_y), "GROUP/STAGE", fill=GOLD_ACCENT, font=label_font)
            group_value = member_data.get('group_stage_name', 'N/A')
            draw.text((col2_x, label_y), group_value, fill=WHITE_TEXT, font=value_font)
            
            # ================================================================
            # 9. CHAIRMAN SECTION - Professional Placement - NO OVERLAP
            # ================================================================
            chairman_y = label_y + 75
            
            # Check if chairman section will overlap with QR code
            qr_size = 260
            qr_y = height - offset_y - qr_size - 80
            
            if chairman_y + 80 > qr_y - 20:
                chairman_y = qr_y - 100
            
            # Chairman label and name
            draw.text((text_x, chairman_y), "CHAIRMAN", fill=GOLD_ACCENT, font=label_font)
            chairman_name = member_data.get('chairman_name', 'N/A')
            draw.text((text_x + 280, chairman_y), chairman_name, fill=WHITE_TEXT, font=value_font)
            
            # Chairman phone (smaller, under chairman name)
            chairman_phone_y = chairman_y + 50
            draw.text((text_x + 280, chairman_phone_y), f"TEL: {member_data.get('chairman_phone', 'N/A')}", 
                     fill=WHITE_TEXT, font=small_font)
            
            # ================================================================
            # 10. QR CODE - Larger, Professional, NO OVERLAPS
            # ================================================================
            qr_size = 260
            qr_x = width - offset_x - qr_size - 40
            
            min_qr_y = chairman_phone_y + 60
            qr_y = max(qr_y, min_qr_y)
            
            # QR shadow
            draw.rounded_rectangle([(qr_x + 4, qr_y + 4), (qr_x + qr_size + 4, qr_y + qr_size + 4)], 
                                 radius=10, fill=(0, 0, 0, 40))
            
            qr_path, qr_filename = QRGenerator.generate_qr(member_data, include_photo=True)
            if os.path.exists(qr_path):
                try:
                    qr_img = Image.open(qr_path)
                    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
                    img.paste(qr_img, (qr_x, qr_y))
                    
                    # QR border - Gold
                    draw.rectangle([(qr_x - 3, qr_y - 3), (qr_x + qr_size + 3, qr_y + qr_size + 3)], 
                                 outline=GOLD_ACCENT, width=3)
                    
                    # "SCAN ME" label - Larger font
                    draw.text((qr_x + qr_size//2, qr_y + qr_size + 22), "SCAN TO VERIFY", 
                             fill=GOLD_ACCENT, font=qr_label_font, anchor='mt')
                except Exception as e:
                    logger.error(f"Error placing QR code: {e}")
            
            # ================================================================
            # 11. FOOTER - Professional with Date, Org, Validity - NO OVERLAP
            # ================================================================
            footer_y = height - offset_y - 60
            
            qr_bottom = qr_y + qr_size + 40
            if footer_y < qr_bottom + 10:
                footer_y = qr_bottom + 10
            
            # Premium footer line
            draw.rectangle([(offset_x + 45, footer_y), (width - offset_x - 45, footer_y + 3)], 
                         fill=GOLD_ACCENT)
            
            # Issue Date
            issue_date = member_data.get('date_registered', datetime.now().strftime('%Y-%m-%d'))
            if isinstance(issue_date, datetime):
                issue_date = issue_date.strftime('%Y-%m-%d')
            
            draw.text((offset_x + 45, footer_y + 14), f"ISSUED: {issue_date}", 
                     fill=WHITE_TEXT, font=small_font)
            
            # Organization Name - Bold and Centered
            draw.text((width//2, footer_y + 14), f"{Config.GROUP_NAME.upper()}", 
                     fill=GOLD_ACCENT, font=logo_font, anchor='mt')
            
            # Validity Date
            draw.text((width - offset_x - 45, footer_y + 14), "VALID UNTIL: 31 DEC 2027", 
                     fill=WHITE_TEXT, font=small_font, anchor='rb')
            
            # ================================================================
            # 12. SUBTLE WATERMARK - Professional Security Feature
            # ================================================================
            if watermark and Config.SHOW_WATERMARK:
                watermark_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
                watermark_draw = ImageDraw.Draw(watermark_img)
                watermark_text = Config.WATERMARK_TEXT
                
                for i in range(-height, height, 140):
                    watermark_draw.text((i, i), watermark_text, fill=(255, 255, 255, 10), 
                                      font=header_font, angle=45)
                
                img = Image.alpha_composite(img.convert('RGBA'), watermark_img).convert('RGB')
            
            # ================================================================
            # 13. CROP MARKS - Professional Print-Ready
            # ================================================================
            if include_bleed:
                crop_color = (255, 255, 255, 120)
                mark_length = 30
                mark_gap = 12
                mark_thickness = 2
                
                # Top-left
                draw.line([(offset_x + mark_gap, offset_y), (offset_x + mark_gap + mark_length, offset_y)], 
                         fill=crop_color, width=mark_thickness)
                draw.line([(offset_x, offset_y + mark_gap), (offset_x, offset_y + mark_gap + mark_length)], 
                         fill=crop_color, width=mark_thickness)
                # Top-right
                draw.line([(width - offset_x - mark_gap, offset_y), (width - offset_x - mark_gap - mark_length, offset_y)], 
                         fill=crop_color, width=mark_thickness)
                draw.line([(width - offset_x, offset_y + mark_gap), (width - offset_x, offset_y + mark_gap + mark_length)], 
                         fill=crop_color, width=mark_thickness)
                # Bottom-left
                draw.line([(offset_x + mark_gap, height - offset_y), (offset_x + mark_gap + mark_length, height - offset_y)], 
                         fill=crop_color, width=mark_thickness)
                draw.line([(offset_x, height - offset_y - mark_gap), (offset_x, height - offset_y - mark_gap + mark_length)], 
                         fill=crop_color, width=mark_thickness)
                # Bottom-right
                draw.line([(width - offset_x - mark_gap, height - offset_y), (width - offset_x - mark_gap - mark_length, height - offset_y)], 
                         fill=crop_color, width=mark_thickness)
                draw.line([(width - offset_x, height - offset_y - mark_gap), (width - offset_x, height - offset_y - mark_gap + mark_length)], 
                         fill=crop_color, width=mark_thickness)
            
            # ================================================================
            # 14. SAVE BADGE - Professional Quality Settings
            # ================================================================
            filename = f"badge_{member_data['member_number']}.png"
            filepath = os.path.join(Config.BADGE_FOLDER, filename)
            
            # Save with print quality settings
            img.save(filepath, 'PNG', quality=98, dpi=(Config.BADGE_DPI, Config.BADGE_DPI))
            
            logger.info(f"Award-winning badge generated for: {member_data['member_number']}")
            return filepath, filename
            
        except Exception as e:
            logger.error(f"Error generating badge: {e}")
            raise
    
    @staticmethod
    def generate_pdf_badge(member_data, include_bleed=False):
        """Generate PDF version of the badge for printing"""
        try:
            from reportlab.lib.pagesizes import landscape, A6
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
            from reportlab.lib import colors
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
            
            # Add subtle background
            c.setFillColor(colors.Color(0.7, 0.08, 0.08, 0.05))
            c.rect(0, 0, page_size[0], page_size[1], fill=1)
            
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
            
            c.setFont("Helvetica", 7)
            c.setFillColor(colors.Color(0.5, 0.5, 0.5))
            c.drawString(10, 10, f"PRINTED: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            c.drawString(10, 5, f"MEMBER: {member_data['member_number']} | {Config.GROUP_NAME}")
            
            c.save()
            logger.info(f"PDF badge generated for member: {member_data['member_number']}")
            return filepath, filename
            
        except Exception as e:
            logger.error(f"Error generating PDF badge: {e}")
            raise
    
    @staticmethod
    def generate_batch_badges(members, include_bleed=False):
        """Generate badges for multiple members"""
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
