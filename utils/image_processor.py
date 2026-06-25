"""
Image processing module for handling passport photos
"""
from PIL import Image, ImageOps
import os
import logging
from config import Config

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Image processing utilities for passport photos"""
    
    @staticmethod
    def resize_passport_photo(input_path, output_path=None):
        """
        Resize and crop passport photo to professional dimensions
        
        Args:
            input_path: Path to input image
            output_path: Path to save resized image (optional)
        
        Returns:
            Path to resized image
        """
        try:
            # Open image
            img = Image.open(input_path)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Target dimensions (passport photo style)
            target_size = (300, 360)  # Width, Height
            
            # Calculate aspect ratios
            img_aspect = img.width / img.height
            target_aspect = target_size[0] / target_size[1]
            
            # Crop to maintain aspect ratio
            if img_aspect > target_aspect:
                # Image is wider - crop width
                new_width = int(img.height * target_aspect)
                left = (img.width - new_width) // 2
                right = left + new_width
                img = img.crop((left, 0, right, img.height))
            else:
                # Image is taller - crop height
                new_height = int(img.width / target_aspect)
                top = (img.height - new_height) // 2
                bottom = top + new_height
                img = img.crop((0, top, img.width, bottom))
            
            # Resize to target
            img = img.resize(target_size, Image.LANCZOS)
            
            # Enhance image quality
            img = ImageOps.autocontrast(img, cutoff=2)
            
            # Save if output path provided
            if output_path:
                img.save(output_path, 'JPEG', quality=95, optimize=True)
                logger.info(f"Image resized and saved to: {output_path}")
                return output_path
            
            return img
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise
    
    @staticmethod
    def create_thumbnail(input_path, output_path=None, size=(150, 150)):
        """
        Create a thumbnail of the image
        
        Args:
            input_path: Path to input image
            output_path: Path to save thumbnail (optional)
            size: Thumbnail dimensions
        
        Returns:
            Path to thumbnail
        """
        try:
            img = Image.open(input_path)
            img.thumbnail(size, Image.LANCZOS)
            
            if output_path:
                img.save(output_path, 'JPEG', quality=85, optimize=True)
                return output_path
            
            return img
            
        except Exception as e:
            logger.error(f"Error creating thumbnail: {e}")
            raise
    
    @staticmethod
    def validate_image(file):
        """
        Validate uploaded image
        
        Args:
            file: File object from request
        
        Returns:
            bool: True if valid, False otherwise
        """
        if not file:
            return False
        
        # Check filename
        if file.filename == '':
            return False
        
        # Check extension
        allowed_extensions = Config.ALLOWED_EXTENSIONS
        if '.' not in file.filename:
            return False
        
        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext not in allowed_extensions:
            return False
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > Config.MAX_CONTENT_LENGTH:
            return False
        
        return True
    
    @staticmethod
    def save_uploaded_file(file, member_number):
        """
        Save uploaded file with proper naming
        
        Args:
            file: File object from request
            member_number: Member number for filename
        
        Returns:
            tuple: (filename, filepath)
        """
        try:
            # Create filename
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{member_number}.{ext}"
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            
            # Save original
            file.save(filepath)
            
            # Process image
            processed_path = ImageProcessor.resize_passport_photo(filepath)
            
            # Create thumbnail
            thumb_filename = f"{member_number}_thumb.{ext}"
            thumb_path = os.path.join(Config.UPLOAD_FOLDER, thumb_filename)
            ImageProcessor.create_thumbnail(filepath, thumb_path)
            
            return filename, processed_path
            
        except Exception as e:
            logger.error(f"Error saving uploaded file: {e}")
            raise
