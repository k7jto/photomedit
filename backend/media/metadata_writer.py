"""Metadata writer using exiftool."""
import subprocess
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from backend.utils.timestamp import format_event_date_for_exif
from backend.utils.sidecar import write_sidecar, get_sidecar_path


class MetadataWriter:
    """Write metadata to media files using exiftool."""
    
    @staticmethod
    def _run_exiftool(file_path: str, tags: Dict[str, str], write_sidecar: bool = False) -> bool:
        """Run exiftool to write tags."""
        try:
            # Check if file is writable
            if not os.access(file_path, os.W_OK):
                import logging
                logging.error(f"File is not writable: {file_path}")
                return False
            
            args = []
            if write_sidecar:
                sidecar_path = get_sidecar_path(file_path)
                args.append(f'-XMP:All<={sidecar_path}')
            
            for key, value in tags.items():
                if value is not None:
                    # Escape special characters in values
                    value_str = str(value).replace('\\', '\\\\').replace('$', '\\$')
                    args.append(f'-{key}={value_str}')
                else:
                    args.append(f'-{key}=')
            
            # Use -overwrite_original to avoid backup files
            cmd = ['exiftool', '-overwrite_original', '-P'] + args + [file_path]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                import logging
                logging.error(f"Exiftool failed: {result.stderr}")
                return False
            
            return True
        except Exception as e:
            import logging
            logging.error(f"Exception in _run_exiftool: {e}")
            return False
    
    @staticmethod
    def write_metadata(file_path: str, metadata: Dict[str, Any], is_image: bool = True) -> bool:
        """
        Write logical metadata to a media file.
        
        For images: writes to both embedded EXIF/IPTC and sidecar XMP
        For videos: writes primarily to sidecar XMP
        """
        tags = {}
        
        # Event date
        event_date = metadata.get('eventDate')
        if event_date:
            from backend.utils.timestamp import parse_event_date
            from datetime import datetime
            # Parse date string if needed
            if isinstance(event_date, str):
                dt = parse_event_date(event_date)
                if dt:
                    precision = metadata.get('eventDatePrecision', 'DAY')
                    formatted_date = format_event_date_for_exif(dt, precision)
                else:
                    # Try to use as-is if it's already in EXIF format
                    formatted_date = event_date
            elif isinstance(event_date, datetime):
                precision = metadata.get('eventDatePrecision', 'DAY')
                formatted_date = format_event_date_for_exif(event_date, precision)
            else:
                formatted_date = str(event_date)
            
            if is_image:
                tags['EXIF:DateTimeOriginal'] = formatted_date
                tags['EXIF:DateTimeDigitized'] = formatted_date
                # Parse date and time for IPTC
                parts = formatted_date.split()
                if len(parts) >= 1:
                    tags['IPTC:DateCreated'] = parts[0].replace(':', '-')
                if len(parts) >= 2:
                    tags['IPTC:TimeCreated'] = parts[1]
                tags['XMP:DateCreated'] = formatted_date
                tags['XMP:photoshop:DateCreated'] = formatted_date
            else:
                tags['XMP:DateCreated'] = formatted_date
        
        # Custom PhotoMedit fields
        if metadata.get('eventDateDisplay'):
            tags['XMP:PhotoMeditEventDateDisplay'] = str(metadata['eventDateDisplay'])
        if metadata.get('eventDatePrecision'):
            tags['XMP:PhotoMeditEventDatePrecision'] = str(metadata['eventDatePrecision'])
        if metadata.get('eventDateApproximate') is not None:
            tags['XMP:PhotoMeditEventDateApproximate'] = 'true' if metadata['eventDateApproximate'] else 'false'
        
        # Subject/Title
        if 'subject' in metadata:
            subject = metadata['subject'] or ''
            if is_image:
                tags['IPTC:ObjectName'] = subject
                tags['XMP:Title'] = subject
                tags['EXIF:XPTitle'] = subject
            else:
                tags['XMP:Title'] = subject
        
        # Notes/Description
        if 'notes' in metadata:
            notes = metadata['notes'] or ''
            if is_image:
                tags['IPTC:Caption-Abstract'] = notes
                tags['XMP:Description'] = notes
                tags['EXIF:ImageDescription'] = notes
                tags['EXIF:XPComment'] = notes
            else:
                tags['XMP:Description'] = notes
        
        # People (keywords)
        if 'people' in metadata:
            people = metadata['people'] or []
            if isinstance(people, list) and people:
                keywords_str = ','.join(str(p) for p in people)
                tags['XMP:Subject'] = keywords_str
                if is_image:
                    tags['IPTC:Keywords'] = keywords_str
        
        # Location
        if 'locationName' in metadata:
            location = metadata['locationName'] or ''
            tags['XMP:Location'] = location
            if is_image:
                tags['IPTC:Location'] = location
        
        # GPS coordinates
        if 'locationCoords' in metadata and metadata['locationCoords']:
            coords = metadata['locationCoords']
            if is_image and coords.get('lat') and coords.get('lon'):
                tags['EXIF:GPSLatitude'] = str(coords['lat'])
                tags['EXIF:GPSLongitude'] = str(coords['lon'])
                tags['EXIF:GPSLatitudeRef'] = 'N' if coords['lat'] >= 0 else 'S'
                tags['EXIF:GPSLongitudeRef'] = 'E' if coords['lon'] >= 0 else 'W'
        
        # Review status
        if 'reviewStatus' in metadata:
            tags['XMP:PhotoMeditReviewStatus'] = str(metadata['reviewStatus'])
        
        # Write to file
        if is_image:
            # Write to both embedded and sidecar
            success = MetadataWriter._run_exiftool(file_path, tags, write_sidecar=False)
            # Also ensure sidecar is updated
            MetadataWriter._run_exiftool(file_path, tags, write_sidecar=True)
            return success
        else:
            # For videos, prefer sidecar
            return MetadataWriter._run_exiftool(file_path, tags, write_sidecar=True)

