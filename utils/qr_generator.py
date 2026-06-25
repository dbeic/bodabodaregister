"""
QR Code generation module
"""
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
import os
import logging
from config import Config

logger = logging.getLogger(__name__)

class QRGenerator:
    """QR Code generator for member badges"""
    
    @staticmethod
    def generate_qr(member_data):
        """
        Generate QR code for member
        
        Args:
            member_data: Dictionary containing member information
        
        Returns:
            Path to generated QR code image
        """
        try:
            # Create QR data string
            qr_data = (
                f"Member: {member_data['member_number']}\n"
                f"Name: {member_data['full_name']}\n"
                f"ID: {member_data['national_id']}\n"
                f"Phone: {member_data['telephone']}\n"
                f"Group: {member_data['group_stage_name']}\n"
                f"Chairman: {member_data['chairman_name']}"
            )
            
            # Generate QR code with high error correction
            qr = qrcode.QRCode(
                version=5,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=12,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create styled QR image
            img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=RoundedModuleDrawer(),
                fill_color='black',
                back_color='white'
            )
            
            # Save QR code
            filename = f"qr_{member_data['member_number']}.png"
            filepath = os.path.join(Config.QR_FOLDER, filename)
            img.save(filepath, 'PNG')
            
            logger.info(f"QR code generated for member: {member_data['member_number']}")
            return filepath, filename
            
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            raise
    
    @staticmethod
    def generate_qr_verification_data(member):
        """Generate QR data for verification"""
        return {
            'member_number': member['member_number'],
            'full_name': member['full_name'],
            'national_id': member['national_id'],
            'telephone': member['telephone'],
            'group': member['group_stage_name']
        }
