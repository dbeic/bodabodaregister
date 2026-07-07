"""
Image processing module for handling passport photos with print-ready quality
"""
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ExifTags
import os
import logging
from config import Config

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Image processing utilities for passport photos and badges"""
    
    @staticmethod
    def normalize_orientation(image):
        """
        Normalize image orientation based on EXIF data.
        Handles rotation and mirroring as needed.
        
        Args:
            image: PIL Image object
        
        Returns:
            PIL Image object with correct orientation
        """
        try:
            # Get EXIF data
            exif = image._getexif()
            if exif:
                # Find orientation tag
                for tag_id, value in exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag_name == 'Orientation':
                        # Apply orientation correction
                        if value == 2:
                            image = image.transpose(Image.FLIP_LEFT_RIGHT)
                        elif value == 3:
                            image = image.rotate(180, expand=True)
                        elif value == 4:
                            image = image.transpose(Image.FLIP_TOP_BOTTOM)
                        elif value == 5:
                            image = image.transpose(Image.FLIP_LEFT_RIGHT).rotate(90, expand=True)
                        elif value == 6:
                            image = image.rotate(270, expand=True)
                        elif value == 7:
                            image = image.transpose(Image.FLIP_LEFT_RIGHT).rotate(270, expand=True)
                        elif value == 8:
                            image = image.rotate(90, expand=True)
                        break
        except Exception as e:
            logger.warning(f"Could not read EXIF orientation: {e}")
        
        return image
    
    @staticmethod
    def resize_passport_photo(input_path, output_path=None, dpi=300):
        """
        Resize and crop passport photo to professional dimensions
        
        Args:
            input_path: Path to input image
            output_path: Path to save resized image (optional)
            dpi: Target DPI for print quality
        
        Returns:
            Path to resized image
        """
        try:
            # Open image
            img = Image.open(input_path)
            
            # Normalize orientation
            img = ImageProcessor.normalize_orientation(img)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Process image
            img = ImageProcessor._resize_passport_photo_internal(img)
            
            # Save with high quality
            if output_path:
                img.save(output_path, 'JPEG', quality=95, optimize=True, dpi=(dpi, dpi))
                logger.info(f"Image resized and saved to: {output_path}")
                return output_path
            
            return img
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise
    
    @staticmethod
    def resize_passport_photo_from_image(img, output_path=None, dpi=300):
        """
        Resize and crop passport photo from PIL Image object
        
        Args:
            img: PIL Image object
            output_path: Path to save resized image (optional)
            dpi: Target DPI for print quality
        
        Returns:
            PIL Image object or path to saved image
        """
        try:
            # Normalize orientation
            img = ImageProcessor.normalize_orientation(img)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Process image
            img = ImageProcessor._resize_passport_photo_internal(img)
            
            if output_path:
                img.save(output_path, 'JPEG', quality=95, optimize=True, dpi=(dpi, dpi))
                logger.info(f"Image resized and saved to: {output_path}")
                return output_path
            
            return img
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise
    
    @staticmethod
    def _resize_passport_photo_internal(img):
        """
        Internal method to resize passport photo
        
        Args:
            img: PIL Image object (already normalized and converted)
        
        Returns:
            PIL Image object
        """
        # Target dimensions (passport photo style at 300 DPI)
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
        
        # Resize to target with high quality
        img = img.resize(target_size, Image.LANCZOS)
        
        # Enhance image quality for print
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2)
        
        # Enhance color
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.05)
        
        # Auto contrast
        img = ImageOps.autocontrast(img, cutoff=2)
        
        return img
    
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
            
            # Normalize orientation for thumbnail
            img = ImageProcessor.normalize_orientation(img)
            
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
            
            # Process image with print quality
            processed_path = ImageProcessor.resize_passport_photo(filepath, dpi=Config.BADGE_DPI)
            
            # Create thumbnail (smaller for preview)
            thumb_filename = f"{member_number}_thumb.{ext}"
            thumb_path = os.path.join(Config.UPLOAD_FOLDER, thumb_filename)
            ImageProcessor.create_thumbnail(filepath, thumb_path, size=(150, 180))
            
            return filename, processed_path
            
        except Exception as e:
            logger.error(f"Error saving uploaded file: {e}")
            raise
    
    @staticmethod
    def prepare_for_print(image_path, output_path=None, dpi=300):
        """
        Prepare image for print with bleed and crop marks
        
        Args:
            image_path: Path to input image
            output_path: Path to save print-ready image (optional)
            dpi: Target DPI
        
        Returns:
            Path to print-ready image
        """
        try:
            img = Image.open(image_path)
            
            # Normalize orientation
            img = ImageProcessor.normalize_orientation(img)
            
            # Convert to CMYK for print
            if img.mode != 'CMYK':
                img = img.convert('CMYK')
            
            # Add bleed area
            bleed = 36  # 0.125 inches at 300 DPI
            width, height = img.size
            new_width = width + (bleed * 2)
            new_height = height + (bleed * 2)
            
            # Create new image with bleed
            new_img = Image.new('CMYK', (new_width, new_height), (0, 0, 0, 0))
            new_img.paste(img, (bleed, bleed))
            
            # Save with print settings
            if output_path:
                new_img.save(output_path, 'TIFF', dpi=(dpi, dpi), compression=None)
                return output_path
            
            return new_img
            
        except Exception as e:
            logger.error(f"Error preparing image for print: {e}")
            raise
