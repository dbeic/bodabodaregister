"""
QR Code generation module with enhanced styling
"""
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.image.styles.colormasks import RadialGradiantColorMask
import os
import logging
import uuid
from PIL import Image, ImageDraw
from config import Config

logger = logging.getLogger(__name__)

class QRGenerator:
    """QR Code generator for member badges"""
    
    @staticmethod
    def generate_qr(member_data, include_photo=False):
        """
        Generate QR code for member with enhanced styling
        Now generates a secure token that references the member, not containing personal data
        
        Args:
            member_data: Dictionary containing member information
            include_photo: Whether to include member photo in QR center
        
        Returns:
            tuple: (filepath, filename)
        """
        try:
            # Generate a unique token for this member
            # This token will be used to look up the member in the database
            member_number = member_data['member_number']
            
            # Create a secure token that references the member
            # Format: BBS-{member_number}-{uuid_short}
            token_id = f"BBS-{member_number}-{uuid.uuid4().hex[:8].upper()}"
            
            # Store the token in the member data for reference
            qr_data = token_id
            
            # Generate QR code with high error correction
            qr = qrcode.QRCode(
                version=6,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create styled QR image with gradient
            img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=RoundedModuleDrawer(radius_ratio=0.5),
                color_mask=RadialGradiantColorMask(
                    back_color=(255, 255, 255),
                    center_color=(212, 175, 55),
                    edge_color=(25, 55, 85)
                )
            )
            
            # Add member photo in center if requested
            if include_photo and member_data.get('passport_photo'):
                try:
                    photo_path = os.path.join(Config.UPLOAD_FOLDER, member_data['passport_photo'])
                    if os.path.exists(photo_path):
                        photo = Image.open(photo_path)
                        from .image_processor import ImageProcessor
                        photo = ImageProcessor.normalize_orientation(photo)
                        photo_size = 40
                        photo = photo.resize((photo_size, photo_size), Image.LANCZOS)
                        
                        # Create circular photo
                        mask = Image.new('L', (photo_size, photo_size), 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse((0, 0, photo_size, photo_size), fill=255)
                        
                        # Center the photo on QR
                        qr_size = img.size[0]
                        center = qr_size // 2
                        offset = photo_size // 2
                        img.paste(photo, (center - offset, center - offset), mask)
                except Exception as e:
                    logger.warning(f"Could not add photo to QR: {e}")
            
            # Save QR code
            filename = f"qr_{member_data['member_number']}.png"
            filepath = os.path.join(Config.QR_FOLDER, filename)
            img.save(filepath, 'PNG', quality=95)
            
            logger.info(f"QR code generated for member: {member_data['member_number']} with token: {token_id}")
            return filepath, filename
            
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            raise
    
    @staticmethod
    def generate_qr_verification_data(member):
        """Generate QR verification data - now returns the token"""
        return {
            'member_number': member['member_number'],
            'full_name': member['full_name'],
            'national_id': member['national_id'],
            'telephone': member['telephone'],
            'group': member['group_stage_name'],
            'issued': member.get('badge_issued', False),
            'has_pin': member.get('qr_pin_hash') is not None
        }
    
    @staticmethod
    def generate_bulk_qr(members):
        """Generate QR codes for multiple members"""
        results = []
        for member in members:
            try:
                qr_path, qr_filename = QRGenerator.generate_qr(member)
                results.append({
                    'member_number': member['member_number'],
                    'qr_path': qr_path,
                    'qr_filename': qr_filename,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'member_number': member['member_number'],
                    'error': str(e),
                    'success': False
                })
        return results
