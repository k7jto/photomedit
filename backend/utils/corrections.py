"""Corrections CSV file management."""
import csv
import os
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

CORRECTIONS_FILENAME = 'corrections.csv'
CSV_FIELDS = ['filename', 'username', 'correction_notes', 'flagged_at', 'cleared_at']


def get_corrections_file_path(folder_path: str) -> str:
    """Get the path to the corrections.csv file in a folder."""
    return os.path.join(folder_path, CORRECTIONS_FILENAME)


def read_corrections(folder_path: str) -> Dict[str, Dict]:
    """
    Read all corrections from a folder's corrections.csv file.
    
    Returns a dict mapping filename -> correction data
    """
    corrections = {}
    csv_path = get_corrections_file_path(folder_path)
    
    if not os.path.exists(csv_path):
        return corrections
    
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                filename = row.get('filename', '')
                if filename and not row.get('cleared_at'):  # Only include active (not cleared) corrections
                    corrections[filename] = {
                        'username': row.get('username', ''),
                        'correctionNotes': row.get('correction_notes', ''),
                        'flaggedAt': row.get('flagged_at', ''),
                        'correctionNeeded': True
                    }
    except Exception as e:
        logger.error(f"Error reading corrections file {csv_path}: {e}")
    
    return corrections


def get_correction(folder_path: str, filename: str) -> Optional[Dict]:
    """Get correction data for a specific file."""
    corrections = read_corrections(folder_path)
    return corrections.get(filename)


def add_correction(folder_path: str, filename: str, username: str, correction_notes: str) -> bool:
    """
    Add or update a correction entry for a file.
    
    If a correction already exists for this file, it will be updated.
    """
    csv_path = get_corrections_file_path(folder_path)
    corrections = []
    found = False
    
    # Read existing corrections
    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('filename') == filename and not row.get('cleared_at'):
                        # Update existing entry
                        row['username'] = username
                        row['correction_notes'] = correction_notes
                        row['flagged_at'] = datetime.utcnow().isoformat() + 'Z'
                        found = True
                    corrections.append(row)
        except Exception as e:
            logger.error(f"Error reading corrections file {csv_path}: {e}")
            return False
    
    # Add new entry if not found
    if not found:
        corrections.append({
            'filename': filename,
            'username': username,
            'correction_notes': correction_notes,
            'flagged_at': datetime.utcnow().isoformat() + 'Z',
            'cleared_at': ''
        })
    
    # Write back to file
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(corrections)
        logger.info(f"Added/updated correction for {filename} in {csv_path}")
        return True
    except Exception as e:
        logger.error(f"Error writing corrections file {csv_path}: {e}")
        return False


def clear_correction(folder_path: str, filename: str) -> bool:
    """
    Clear a correction entry for a file (mark as resolved).
    
    Instead of deleting, we set the cleared_at timestamp for audit trail.
    """
    csv_path = get_corrections_file_path(folder_path)
    
    if not os.path.exists(csv_path):
        return True  # Nothing to clear
    
    corrections = []
    found = False
    
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('filename') == filename and not row.get('cleared_at'):
                    # Mark as cleared
                    row['cleared_at'] = datetime.utcnow().isoformat() + 'Z'
                    found = True
                corrections.append(row)
    except Exception as e:
        logger.error(f"Error reading corrections file {csv_path}: {e}")
        return False
    
    if not found:
        return True  # Nothing to clear
    
    # Write back to file
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(corrections)
        logger.info(f"Cleared correction for {filename} in {csv_path}")
        return True
    except Exception as e:
        logger.error(f"Error writing corrections file {csv_path}: {e}")
        return False


def list_corrections_in_folder(folder_path: str) -> List[Dict]:
    """List all active corrections in a folder."""
    corrections = read_corrections(folder_path)
    return [
        {'filename': filename, **data}
        for filename, data in corrections.items()
    ]

