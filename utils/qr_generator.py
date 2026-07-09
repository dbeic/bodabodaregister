"""
QR Code generation module with PIN-protected data
"""
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.image.styles.colormasks import RadialGradiantColorMask
import os
import logging
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from PIL import Image, ImageDraw
from config import Config

logger = logging.getLogger(__name__)

class QRGenerator:
    """QR Code generator for member badges with PIN protection"""
    
    # Secret key for encryption (should be in environment in production)
    _encryption_salt = b'qr_pin_salt_bbs_2026'
    
    @staticmethod
    def _derive_key(pin, salt=None):
        """Derive encryption key from PIN"""
        if salt is None:
            salt = QRGenerator._encryption_salt
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(pin.encode()))
        return key
    
    @staticmethod
    def encrypt_data(data, pin):
        """Encrypt QR data with PIN"""
        try:
            key = QRGenerator._derive_key(pin)
            cipher = Fernet(key)
            encrypted = cipher.encrypt(json.dumps(data).encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Error encrypting QR data: {e}")
            raise
    
    @staticmethod
    def decrypt_data(encrypted_data, pin):
        """Decrypt QR data with PIN"""
        try:
            key = QRGenerator._derive_key(pin)
            cipher = Fernet(key)
            decrypted = cipher.decrypt(base64.urlsafe_b64decode(encrypted_data))
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Error decrypting QR data: {e}")
            raise
    
    @staticmethod
    def generate_qr(member_data, include_photo=False, pin=None):
        """
        Generate QR code for member with PIN-protected data
        
        Args:
            member_data: Dictionary containing member information
            include_photo: Whether to include member photo in QR center
            pin: PIN for encrypting QR data (if None, data is not encrypted)
        
        Returns:
            tuple: (filepath, filename, encrypted_data)
        """
        try:
            # Prepare QR data
            qr_data_payload = {
                'member': member_data['member_number'],
                'name': member_data['full_name'],
                'id': member_data['national_id'],
                'phone': member_data['telephone'],
                'group': member_data.get('group_stage_name', ''),
                'chairman': member_data.get('chairman_name', ''),
                'issued': member_data.get('badge_issued', False)
            }
            
            # Encrypt data if PIN is provided
            if pin:
                encrypted_data = QRGenerator.encrypt_data(qr_data_payload, pin)
                qr_data = f"BBSQR:{encrypted_data}"
            else:
                # Fallback: embed data directly (for backward compatibility)
                qr_data = (
                    f"Member: {member_data['member_number']}\n"
                    f"Name: {member_data['full_name']}\n"
                    f"ID: {member_data['national_id']}\n"
                    f"Phone: {member_data['telephone']}\n"
                    f"Group: {member_data['group_stage_name']}\n"
                    f"Chairman: {member_data['chairman_name']}\n"
                    f"Verified: {member_data.get('badge_issued', False)}"
                )
                encrypted_data = None
            
            # Generate QR code with high error correction
            qr = qrcode.QRCode(
                version=6,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create styled QR image
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
                        photo_size = 40
                        photo = photo.resize((photo_size, photo_size), Image.LANCZOS)
                        
                        mask = Image.new('L', (photo_size, photo_size), 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse((0, 0, photo_size, photo_size), fill=255)
                        
                        qr_size = img.size[0]
                        center = qr_size // 2
                        offset = photo_size // 2
                        img.paste(photo, (center - offset, center - offset), mask)
                except Exception as e:
                    logger.warning(f"Could not add photo to QR: {e}")
            
            # Add PIN indicator if encrypted
            if pin:
                draw = ImageDraw.Draw(img)
                try:
                    small_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 12)
                except:
                    small_font = ImageFont.load_default()
                draw.text((10, img.size[1] - 20), "🔒 PIN Protected", fill=(255, 255, 255), font=small_font)
            
            # Save QR code
            filename = f"qr_{member_data['member_number']}.png"
            filepath = os.path.join(Config.QR_FOLDER, filename)
            img.save(filepath, 'PNG', quality=95)
            
            logger.info(f"QR code generated for member: {member_data['member_number']}")
            return filepath, filename, encrypted_data
            
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            raise
    
    @staticmethod
    def decrypt_qr_data(qr_content, pin):
        """
        Decrypt QR data from QR code content
        
        Args:
            qr_content: The scanned QR code content
            pin: The PIN provided by the user
        
        Returns:
            dict: Decrypted member data
        """
        try:
            if qr_content.startswith('BBSQR:'):
                encrypted_part = qr_content[6:]  # Remove 'BBSQR:' prefix
                return QRGenerator.decrypt_data(encrypted_part, pin)
            else:
                # Legacy format - parse directly
                data = {}
                for line in qr_content.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        data[key.strip().lower()] = value.strip()
                return data
        except Exception as e:
            logger.error(f"Error decrypting QR data: {e}")
            raise ValueError("Invalid PIN or corrupted QR data")
    
    @staticmethod
    def generate_bulk_qr(members, pin=None):
        """Generate QR codes for multiple members"""
        results = []
        for member in members:
            try:
                qr_path, qr_filename, encrypted = QRGenerator.generate_qr(member, pin=pin)
                results.append({
                    'member_number': member['member_number'],
                    'qr_path': qr_path,
                    'qr_filename': qr_filename,
                    'encrypted': encrypted is not None,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'member_number': member['member_number'],
                    'error': str(e),
                    'success': False
                })
        return results
