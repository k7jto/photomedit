"""Metadata reader using exiftool."""
import subprocess
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from backend.utils.sidecar import read_sidecar, get_sidecar_path


class MetadataReader:
    """Read metadata from media files using exiftool."""
    
    @staticmethod
    def _run_exiftool(file_path: str, args: list = None) -> Optional[Dict[str, Any]]:
        """Run exiftool and return JSON output."""
        if args is None:
            args = []
        
        try:
            # Use -ext xmp to also read from sidecar files automatically
            # Exiftool will read from both the main file and associated .xmp sidecar
            cmd = ['exiftool', '-j', '-struct', '-G'] + args + [file_path]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                if data and len(data) > 0:
                    return data[0]
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def read_technical_metadata(file_path: str) -> Dict[str, Any]:
        """Read technical metadata (read-only fields)."""
        metadata = {}
        
        exif_data = MetadataReader._run_exiftool(file_path)
        if not exif_data:
            return metadata
        
        # Extract technical fields
        metadata['fileSize'] = exif_data.get('File:FileSize')
        metadata['mimeType'] = exif_data.get('File:MIMEType')
        
        # Image-specific
        if 'EXIF:ImageWidth' in exif_data:
            metadata['width'] = exif_data.get('EXIF:ImageWidth')
            metadata['height'] = exif_data.get('EXIF:ImageHeight')
            metadata['orientation'] = exif_data.get('EXIF:Orientation')
            metadata['colorSpace'] = exif_data.get('EXIF:ColorSpace')
            metadata['make'] = exif_data.get('EXIF:Make')
            metadata['model'] = exif_data.get('EXIF:Model')
            metadata['iso'] = exif_data.get('EXIF:ISO')
            metadata['fNumber'] = exif_data.get('EXIF:FNumber')
            metadata['exposureTime'] = exif_data.get('EXIF:ExposureTime')
            metadata['focalLength'] = exif_data.get('EXIF:FocalLength')
        
        # Video-specific
        if 'QuickTime:VideoFrameRate' in exif_data:
            metadata['width'] = exif_data.get('QuickTime:ImageWidth') or exif_data.get('Track1:VideoFrameSize', '').split('x')[0]
            metadata['height'] = exif_data.get('QuickTime:ImageHeight') or exif_data.get('Track1:VideoFrameSize', '').split('x')[-1]
            metadata['frameRate'] = exif_data.get('QuickTime:VideoFrameRate')
            metadata['duration'] = exif_data.get('QuickTime:Duration')
            metadata['codec'] = exif_data.get('QuickTime:CompressorID')
        
        return metadata
    
    @staticmethod
    def read_logical_metadata(file_path: str) -> Dict[str, Any]:
        """Read logical metadata (editable fields)."""
        metadata = {}
        
        # Check sidecar first
        sidecar_content = read_sidecar(file_path)
        if sidecar_content:
            # Parse XMP from sidecar (simplified - in production use proper XMP parser)
            # For now, we'll read from exiftool which handles XMP
            pass
        
        # Read metadata - exiftool automatically reads from sidecar .xmp files if they exist
        # Use -ext xmp to ensure sidecar files are also considered
        exif_data = MetadataReader._run_exiftool(file_path, ['-XMP:All', '-IPTC:All', '-EXIF:DateTimeOriginal', '-EXIF:ImageDescription'])
        if not exif_data:
            return metadata
        
        # Also try reading directly from sidecar if it exists (for XMP tags)
        from backend.utils.sidecar import sidecar_exists
        if sidecar_exists(file_path):
            sidecar_data = MetadataReader._run_exiftool(get_sidecar_path(file_path), ['-XMP:All'])
            if sidecar_data:
                # Merge sidecar data, with sidecar taking precedence for XMP tags
                for key, value in sidecar_data.items():
                    if key.startswith('XMP:') and value:
                        exif_data[key] = value
        
        # Event date
        event_date = (
            exif_data.get('EXIF:DateTimeOriginal') or
            exif_data.get('XMP:DateCreated') or
            exif_data.get('IPTC:DateCreated')
        )
        if event_date:
            metadata['eventDate'] = event_date
        
        # Custom PhotoMedit fields from XMP
        metadata['eventDateDisplay'] = exif_data.get('XMP:PhotoMeditEventDateDisplay')
        metadata['eventDatePrecision'] = exif_data.get('XMP:PhotoMeditEventDatePrecision', 'UNKNOWN')
        metadata['eventDateApproximate'] = exif_data.get('XMP:PhotoMeditEventDateApproximate', 'false').lower() == 'true'
        
        # Subject/Title
        metadata['subject'] = (
            exif_data.get('XMP:Title') or
            exif_data.get('IPTC:ObjectName') or
            exif_data.get('EXIF:XPTitle')
        )
        
        # Notes/Description
        metadata['notes'] = (
            exif_data.get('XMP:Description') or
            exif_data.get('IPTC:Caption-Abstract') or
            exif_data.get('EXIF:ImageDescription')
        )
        
        # People (from keywords/subjects)
        people = []
        keywords = exif_data.get('XMP:Subject', [])
        if isinstance(keywords, str):
            keywords = [keywords]
        for kw in keywords:
            if kw and isinstance(kw, str):
                people.append(kw)
        metadata['people'] = people
        
        # Location
        metadata['locationName'] = exif_data.get('XMP:Location') or exif_data.get('IPTC:Location')
        
        # GPS coordinates
        lat = exif_data.get('EXIF:GPSLatitude')
        lon = exif_data.get('EXIF:GPSLongitude')
        if lat and lon:
            metadata['locationCoords'] = {'lat': float(lat), 'lon': float(lon)}
        
        # Review status - read from XMP:UserComment with PhotoMedit prefix
        # Only use UserComment if it contains PhotoMedit prefix (not used for Notes)
        # Format: "PhotoMedit:reviewed" or "PhotoMedit:unreviewed"
        user_comment = exif_data.get('XMP:UserComment', '')
        notes = metadata.get('notes', '')
        review_status = 'unreviewed'  # Default
        
        # Check if UserComment is PhotoMedit-specific (starts with "PhotoMedit:")
        # Also check that UserComment is different from Notes (to avoid false positives)
        if isinstance(user_comment, str) and user_comment.startswith('PhotoMedit:'):
            status_part = user_comment.split(':', 1)[1].strip().lower()
            if status_part in ['reviewed', 'unreviewed']:
                review_status = status_part
        elif isinstance(user_comment, str) and user_comment.strip() and user_comment.strip() == notes.strip():
            # UserComment is being used for Notes, so don't use it for review status
            review_status = 'unreviewed'
        
        metadata['reviewStatus'] = review_status
        
        # Note: Correction flags are stored in corrections.csv, not in image metadata
        # They are loaded separately in the media routes
        
        return metadata

