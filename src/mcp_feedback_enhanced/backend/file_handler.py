"""
File Handling for MCP Feedback Enhanced

This module provides file upload, processing, and management functionality.
Supports image validation, thumbnail generation, and secure file storage.
"""

import base64
import hashlib
import logging
import mimetypes
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageOps
from PIL.ExifTags import TAGS

from .config import get_settings
from .models import ImageModel

logger = logging.getLogger(__name__)


class FileHandler:
    """
    Handles file upload, processing, and storage operations.
    
    Features:
    - Image validation and processing
    - Thumbnail generation
    - EXIF data extraction and cleaning
    - Secure file storage
    - File type validation
    - Size limit enforcement
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.upload_dir = self.settings.upload_dir
        self.max_file_size = self.settings.max_file_size
        self.allowed_types = self.settings.allowed_file_types
        
        # Ensure upload directory exists
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
    def validate_file_type(self, content_type: str) -> bool:
        """
        Validate file content type
        
        Args:
            content_type: MIME type of the file
            
        Returns:
            True if file type is allowed, False otherwise
        """
        return content_type in self.allowed_types
        
    def validate_file_size(self, size: int) -> bool:
        """
        Validate file size
        
        Args:
            size: File size in bytes
            
        Returns:
            True if file size is within limits, False otherwise
        """
        return 0 < size <= self.max_file_size
        
    def decode_base64_image(self, data: str) -> Tuple[bytes, str]:
        """
        Decode base64 image data
        
        Args:
            data: Base64 encoded image data (with or without data URL prefix)
            
        Returns:
            Tuple of (image_bytes, content_type)
            
        Raises:
            ValueError: If data is invalid or unsupported format
        """
        try:
            # Remove data URL prefix if present
            if data.startswith("data:"):
                header, data = data.split(",", 1)
                # Extract content type from header
                content_type = header.split(":")[1].split(";")[0]
            else:
                content_type = None
                
            # Decode base64 data
            image_bytes = base64.b64decode(data)
            
            # Validate decoded data
            if not image_bytes:
                raise ValueError("Empty image data")
                
            # Detect content type if not provided
            if not content_type:
                content_type = self._detect_image_type(image_bytes)
                
            return image_bytes, content_type
            
        except Exception as e:
            raise ValueError(f"Invalid base64 image data: {e}")
            
    def _detect_image_type(self, image_bytes: bytes) -> str:
        """
        Detect image content type from bytes
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            MIME type string
            
        Raises:
            ValueError: If image type cannot be detected
        """
        # Check magic bytes for common image formats
        if image_bytes.startswith(b'\xff\xd8\xff'):
            return "image/jpeg"
        elif image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            return "image/png"
        elif image_bytes.startswith(b'GIF87a') or image_bytes.startswith(b'GIF89a'):
            return "image/gif"
        elif image_bytes.startswith(b'RIFF') and b'WEBP' in image_bytes[:12]:
            return "image/webp"
        else:
            raise ValueError("Unsupported image format")
            
    def process_image(self, image_bytes: bytes, content_type: str, filename: str) -> ImageModel:
        """
        Process uploaded image
        
        Args:
            image_bytes: Raw image bytes
            content_type: MIME type
            filename: Original filename
            
        Returns:
            Processed ImageModel
            
        Raises:
            ValueError: If image processing fails
        """
        try:
            # Validate file type and size
            if not self.validate_file_type(content_type):
                raise ValueError(f"File type {content_type} not allowed")
                
            if not self.validate_file_size(len(image_bytes)):
                raise ValueError(f"File size {len(image_bytes)} exceeds limit {self.max_file_size}")
                
            # Open image with PIL
            with Image.open(BytesIO(image_bytes)) as img:
                # Get image dimensions
                width, height = img.size
                
                # Clean EXIF data and fix orientation
                img = ImageOps.exif_transpose(img)
                
                # Convert to RGB if necessary (for JPEG compatibility)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparency
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Generate thumbnail
                thumbnail_data = self._generate_thumbnail(img)
                
                # Convert processed image back to bytes
                output = BytesIO()
                img.save(output, format='JPEG', quality=85, optimize=True)
                processed_bytes = output.getvalue()
                
                # Encode to base64
                image_data = base64.b64encode(processed_bytes).decode('utf-8')
                
                # Create ImageModel
                image_model = ImageModel(
                    filename=filename,
                    content_type="image/jpeg",  # Always save as JPEG after processing
                    size=len(processed_bytes),
                    data=image_data,
                    thumbnail=thumbnail_data,
                    width=img.width,
                    height=img.height
                )
                
                logger.info(f"Processed image {filename}: {width}x{height}, {len(image_bytes)} -> {len(processed_bytes)} bytes")
                return image_model
                
        except Exception as e:
            logger.error(f"Error processing image {filename}: {e}")
            raise ValueError(f"Image processing failed: {e}")
            
    def _generate_thumbnail(self, img: Image.Image, size: Tuple[int, int] = (150, 150)) -> str:
        """
        Generate thumbnail from image
        
        Args:
            img: PIL Image object
            size: Thumbnail size (width, height)
            
        Returns:
            Base64 encoded thumbnail data
        """
        try:
            # Create thumbnail
            thumbnail = img.copy()
            thumbnail.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Save thumbnail to bytes
            output = BytesIO()
            thumbnail.save(output, format='JPEG', quality=75, optimize=True)
            thumbnail_bytes = output.getvalue()
            
            # Encode to base64
            return base64.b64encode(thumbnail_bytes).decode('utf-8')
            
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail: {e}")
            return ""
            
    def save_image_to_disk(self, image_model: ImageModel, session_id: str) -> Path:
        """
        Save image to disk storage
        
        Args:
            image_model: Image model to save
            session_id: Session ID for organization
            
        Returns:
            Path to saved file
        """
        try:
            # Create session directory
            session_dir = self.upload_dir / session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate safe filename
            safe_filename = self._generate_safe_filename(image_model.filename, image_model.id)
            file_path = session_dir / safe_filename
            
            # Decode and save image data
            image_bytes = base64.b64decode(image_model.data)
            file_path.write_bytes(image_bytes)
            
            logger.info(f"Saved image to disk: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving image to disk: {e}")
            raise ValueError(f"Failed to save image: {e}")
            
    def _generate_safe_filename(self, original_filename: str, image_id: str) -> str:
        """
        Generate safe filename for storage
        
        Args:
            original_filename: Original filename
            image_id: Unique image ID
            
        Returns:
            Safe filename string
        """
        # Extract extension
        ext = Path(original_filename).suffix.lower()
        if not ext:
            ext = '.jpg'
            
        # Create safe filename with timestamp and ID
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = f"{timestamp}_{image_id[:8]}{ext}"
        
        return safe_name
        
    def cleanup_session_files(self, session_id: str) -> bool:
        """
        Clean up files for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            session_dir = self.upload_dir / session_id
            if session_dir.exists():
                # Remove all files in session directory
                for file_path in session_dir.iterdir():
                    if file_path.is_file():
                        file_path.unlink()
                        
                # Remove directory if empty
                try:
                    session_dir.rmdir()
                except OSError:
                    pass  # Directory not empty
                    
                logger.info(f"Cleaned up files for session {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error cleaning up session files {session_id}: {e}")
            
        return False
        
    def get_storage_stats(self) -> Dict[str, any]:
        """
        Get storage statistics
        
        Returns:
            Dictionary with storage statistics
        """
        try:
            total_size = 0
            file_count = 0
            session_count = 0
            
            if self.upload_dir.exists():
                for session_dir in self.upload_dir.iterdir():
                    if session_dir.is_dir():
                        session_count += 1
                        for file_path in session_dir.iterdir():
                            if file_path.is_file():
                                total_size += file_path.stat().st_size
                                file_count += 1
                                
            return {
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_count": file_count,
                "session_count": session_count,
                "upload_dir": str(self.upload_dir)
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {
                "error": str(e)
            }


# Global file handler instance
file_handler = FileHandler()


def get_file_handler() -> FileHandler:
    """Get the global file handler instance"""
    return file_handler
