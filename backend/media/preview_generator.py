"""Preview and thumbnail generator."""
import os
import hashlib
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import rawpy


class PreviewGenerator:
    """Generate thumbnails and previews for media files."""
    
    def __init__(self, cache_root: str):
        self.cache_root = cache_root
        os.makedirs(cache_root, exist_ok=True)
    
    def _get_cache_path(self, media_path: str, size: str = 'thumb') -> str:
        """Get cache path for a media file."""
        # Create hash-based cache key
        path_hash = hashlib.md5(media_path.encode()).hexdigest()
        mtime = os.path.getmtime(media_path)
        cache_key = f"{path_hash}_{int(mtime)}_{size}"
        
        # Organize by date (YYYYMMDD)
        from datetime import datetime
        date_dir = datetime.now().strftime('%Y%m%d')
        cache_dir = os.path.join(self.cache_root, date_dir)
        os.makedirs(cache_dir, exist_ok=True)
        
        return os.path.join(cache_dir, f"{cache_key}.jpg")
    
    def generate_image_thumbnail(self, image_path: str, max_size: Tuple[int, int] = (300, 300)) -> Optional[str]:
        """Generate thumbnail for an image."""
        cache_path = self._get_cache_path(image_path, 'thumb')
        
        # Return cached if exists
        if os.path.exists(cache_path):
            return cache_path
        
        try:
            ext = Path(image_path).suffix.lower()
            
            # For JPEGs, we can serve directly, but generate thumbnail for consistency
            # Handle RAW files
            if ext in ['.orf', '.nef', '.cr2', '.cr3', '.raf', '.arw', '.dng']:
                with rawpy.imread(image_path) as raw:
                    rgb = raw.postprocess()
                    img = Image.fromarray(rgb)
            else:
                # Regular image
                img = Image.open(image_path)
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
            
            # Resize maintaining aspect ratio
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save to cache
            img.save(cache_path, 'JPEG', quality=85)
            return cache_path
            
        except Exception as e:
            import logging
            logging.error(f"Thumbnail generation failed for {image_path}: {e}")
            return None
    
    def generate_video_thumbnail(self, video_path: str, max_size: Tuple[int, int] = (300, 300)) -> Optional[str]:
        """Generate thumbnail for a video using ffmpeg."""
        cache_path = self._get_cache_path(video_path, 'thumb')
        
        # Return cached if exists
        if os.path.exists(cache_path):
            return cache_path
        
        try:
            # Get video duration
            probe_cmd = [
                'ffprobe', '-v', 'error', '-show_entries',
                'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
            duration = float(result.stdout.strip()) if result.returncode == 0 else 1.0
            
            # Extract frame at 10% of duration
            seek_time = duration * 0.1
            
            # Extract frame
            extract_cmd = [
                'ffmpeg', '-i', video_path,
                '-ss', str(seek_time),
                '-vframes', '1',
                '-vf', f'scale={max_size[0]}:{max_size[1]}:force_original_aspect_ratio=decrease',
                '-y', cache_path
            ]
            
            result = subprocess.run(extract_cmd, capture_output=True, timeout=30)
            if result.returncode == 0 and os.path.exists(cache_path):
                return cache_path
        except Exception:
            pass
        
        return None
    
    def generate_preview(self, media_path: str, is_image: bool = True, max_size: Tuple[int, int] = (1920, 1920)) -> Optional[str]:
        """Generate preview (larger than thumbnail)."""
        cache_path = self._get_cache_path(media_path, 'preview')
        
        # Return cached if exists
        if os.path.exists(cache_path):
            return cache_path
        
        if is_image:
            try:
                ext = Path(media_path).suffix.lower()
                
                if ext in ['.orf', '.nef', '.cr2', '.cr3', '.raf', '.arw', '.dng']:
                    with rawpy.imread(media_path) as raw:
                        rgb = raw.postprocess()
                        img = Image.fromarray(rgb)
                else:
                    img = Image.open(media_path)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                
                # Resize maintaining aspect ratio
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save to cache
                img.save(cache_path, 'JPEG', quality=90)
                return cache_path
            except Exception:
                return None
        else:
            # For videos, return thumbnail as preview for now
            return self.generate_video_thumbnail(media_path, max_size)

