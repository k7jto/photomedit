"""Metadata writer using exiftool."""
import subprocess
import os
import logging
from pathlib import Path
from typing import Dict, Any
from backend.utils.timestamp import format_event_date_for_exif

logger = logging.getLogger(__name__)


class MetadataWriter:
    """Write metadata to media files using exiftool."""
    
    @staticmethod
    def _run_exiftool(file_path: str, tags: Dict[str, str], write_sidecar: bool = False) -> bool:
        """Run exiftool to write tags."""
        try:
            # Check if file is writable
            if not os.access(file_path, os.W_OK):
                logger.error(f"File is not writable: {file_path}")
                return False
            
            args = []
            if write_sidecar:
                # For sidecar writes, use -o to write XMP tags to sidecar file
                from backend.utils.sidecar import get_sidecar_path
                sidecar_path = get_sidecar_path(file_path)
                # Ensure sidecar directory exists
                os.makedirs(os.path.dirname(sidecar_path), exist_ok=True)
                # Use -o to write to sidecar file
                args.append('-o')
                args.append(sidecar_path)
            
            for key, value in tags.items():
                if value is not None and value != '':
                    # Escape special characters in values
                    value_str = str(value).replace('\\', '\\\\').replace('$', '\\$')
                    # Standard tag format: -TagName=value
                    args.append(f'-{key}={value_str}')
            
            # Use -overwrite_original to avoid backup files, -P to preserve file modification date
            # -m to ignore minor errors
            if write_sidecar:
                # For sidecar, don't use -overwrite_original (we're writing to a different file)
                cmd = ['exiftool', '-P', '-m'] + args + [file_path]
            else:
                cmd = ['exiftool', '-overwrite_original', '-P', '-m'] + args + [file_path]
            
            logger.debug(f"Running exiftool: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Exiftool failed for {file_path}: {result.stderr}")
                logger.debug(f"Exiftool stdout: {result.stdout}")
                return False
            
            logger.info(f"Successfully wrote metadata to {file_path}")
            return True
        except subprocess.TimeoutExpired:
            logger.error(f"Exiftool timed out for {file_path}")
            return False
        except Exception as e:
            logger.error(f"Exception in _run_exiftool for {file_path}: {e}", exc_info=True)
            return False
    
    @staticmethod
    def _parse_location_name(location_name: str) -> tuple:
        """Parse location name into city and country if possible."""
        # Simple parsing: assume format like "City, Country" or just "City"
        # This is a basic implementation - could be enhanced with geocoding
        if not location_name:
            return None, None
        
        parts = [p.strip() for p in location_name.split(',')]
        if len(parts) >= 2:
            city = parts[0]
            country = parts[-1]
            return city, country
        elif len(parts) == 1:
            # If only one part, assume it's a city
            return parts[0], None
        return None, None
    
    @staticmethod
    def write_metadata(file_path: str, metadata: Dict[str, Any], is_image: bool = True) -> bool:
        """
        Write logical metadata to a media file.
        
        For images: writes to both embedded EXIF/IPTC and sidecar XMP
        For videos: writes primarily to sidecar XMP
        
        Follows the final metadata strategy:
        - Date: XMP-exif:DateTimeOriginal, EXIF:DateTimeOriginal, EXIF:CreateDate, EXIF:ModifyDate
        - Subject/Notes: XMP-dc:description, IPTC:Caption-Abstract
        - Location: XMP-photoshop:City, XMP-photoshop:Country, IPTC:City, IPTC:Country-PrimaryLocationName
        - People/Keywords: XMP-dc:subject[], IPTC:Keywords[]
        - Title: XMP-dc:title, IPTC:ObjectName
        """
        tags = {}
        
        # Event date - write to all specified tags
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
            
            if formatted_date:
                # Write to all date tags as specified
                tags['XMP-exif:DateTimeOriginal'] = formatted_date
                if is_image:
                    tags['EXIF:DateTimeOriginal'] = formatted_date
                    tags['EXIF:CreateDate'] = formatted_date
                    tags['EXIF:ModifyDate'] = formatted_date
        
        # Custom PhotoMedit fields
        if metadata.get('eventDateDisplay'):
            tags['XMP:PhotoMeditEventDateDisplay'] = str(metadata['eventDateDisplay'])
        if metadata.get('eventDatePrecision'):
            tags['XMP:PhotoMeditEventDatePrecision'] = str(metadata['eventDatePrecision'])
        if metadata.get('eventDateApproximate') is not None:
            tags['XMP:PhotoMeditEventDateApproximate'] = 'true' if metadata['eventDateApproximate'] else 'false'
        
        # Title (Subject)
        if 'subject' in metadata:
            subject = metadata['subject'] or ''
            if subject:
                tags['XMP-dc:title'] = subject
                if is_image:
                    tags['IPTC:ObjectName'] = subject
        
        # Notes/Description
        if 'notes' in metadata:
            notes = metadata['notes'] or ''
            if notes:
                tags['XMP-dc:description'] = notes
                if is_image:
                    tags['IPTC:Caption-Abstract'] = notes
        
        # People (Keywords)
        if 'people' in metadata:
            people = metadata['people'] or []
            if isinstance(people, list) and people:
                # For XMP-dc:subject, exiftool expects array format
                # We'll write each person as a separate subject tag
                people_list = [str(p).strip() for p in people if p and str(p).strip()]
                if people_list:
                    # IPTC:Keywords accepts comma-separated or can be written multiple times
                    keywords_str = ','.join(people_list)
                    if is_image:
                        tags['IPTC:Keywords'] = keywords_str
                    
                    # XMP-dc:subject - write as comma-separated, exiftool will parse as array
                    tags['XMP-dc:subject'] = ','.join(people_list)
        
        # Location
        if 'locationName' in metadata:
            location = metadata['locationName'] or ''
            if location:
                city, country = MetadataWriter._parse_location_name(location)
                if city:
                    tags['XMP-photoshop:City'] = city
                    if is_image:
                        tags['IPTC:City'] = city
                if country:
                    tags['XMP-photoshop:Country'] = country
                    if is_image:
                        tags['IPTC:Country-PrimaryLocationName'] = country
        
        # GPS coordinates
        if 'locationCoords' in metadata and metadata['locationCoords']:
            coords = metadata['locationCoords']
            if is_image and coords.get('lat') is not None and coords.get('lon') is not None:
                tags['EXIF:GPSLatitude'] = str(coords['lat'])
                tags['EXIF:GPSLongitude'] = str(coords['lon'])
                tags['EXIF:GPSLatitudeRef'] = 'N' if coords['lat'] >= 0 else 'S'
                tags['EXIF:GPSLongitudeRef'] = 'E' if coords['lon'] >= 0 else 'W'
        
        # Review status - use XMP:UserComment with PhotoMedit prefix
        # Only use UserComment if it's different from Notes (to avoid overwriting Notes stored in UserComment)
        # Format: "PhotoMedit:reviewed" or "PhotoMedit:unreviewed"
        if 'reviewStatus' in metadata:
            review_value = str(metadata['reviewStatus']).lower()
            logger.info(f"Writing review status '{review_value}' to {file_path}")
            
            # Read existing UserComment directly from exif_data to avoid recursion
            from backend.media.metadata_reader import MetadataReader as MR
            existing_exif = MR._run_exiftool(file_path, ['-XMP:UserComment', '-XMP:Description', '-IPTC:Caption-Abstract'])
            logger.debug(f"Read existing exif data: {existing_exif}")
            existing_user_comment = (existing_exif.get('XMP:UserComment', '') if existing_exif else '') or ''
            existing_notes = (
                (existing_exif.get('XMP:Description', '') if existing_exif else '') or
                (existing_exif.get('IPTC:Caption-Abstract', '') if existing_exif else '') or
                ''
            )
            
            logger.debug(f"Existing UserComment: '{existing_user_comment}', Existing Notes: '{existing_notes}'")
            
            # Check if UserComment is different from Notes
            # If UserComment is the same as Notes, we shouldn't overwrite it
            # If UserComment is empty or PhotoMedit-prefixed, we can use it
            notes_in_usercomment = (
                existing_user_comment and 
                existing_notes and 
                existing_user_comment.strip() == existing_notes.strip()
            )
            
            # Only write to UserComment if:
            # 1. It's empty, OR
            # 2. It's already PhotoMedit-prefixed, OR  
            # 3. It's different from Notes
            if not notes_in_usercomment or existing_user_comment.startswith('PhotoMedit:'):
                tags['XMP:UserComment'] = f'PhotoMedit:{review_value}'
                logger.info(f"Will write review status to UserComment: 'PhotoMedit:{review_value}'")
            else:
                logger.warning(f"Skipping review status write - UserComment contains Notes: '{existing_user_comment}'")
            # If UserComment contains Notes and is not PhotoMedit-prefixed, we skip writing review status
            # (in this case, review status won't be persisted - could use a different field)
        
        # Write to file
        if is_image:
            # Write to embedded metadata first (all tags)
            embedded_success = MetadataWriter._run_exiftool(file_path, tags, write_sidecar=False)
            
            # Also write XMP tags to sidecar file
            # Extract only XMP tags for sidecar
            xmp_tags = {k: v for k, v in tags.items() if k.startswith('XMP')}
            if xmp_tags:
                sidecar_success = MetadataWriter._run_exiftool(file_path, xmp_tags, write_sidecar=True)
            else:
                sidecar_success = True  # No XMP tags to write
            
            return embedded_success and sidecar_success
        else:
            # For videos, write primarily to sidecar (XMP tags only)
            xmp_tags = {k: v for k, v in tags.items() if k.startswith('XMP')}
            if xmp_tags:
                return MetadataWriter._run_exiftool(file_path, xmp_tags, write_sidecar=True)
            return True
