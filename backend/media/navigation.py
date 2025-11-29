"""Media navigation utilities."""
from typing import Optional, List, Dict, Any
from backend.libraries.filesystem import scan_media_files
from backend.media.metadata_reader import MetadataReader


class MediaNavigator:
    """Navigate between media items."""
    
    @staticmethod
    def get_media_list(root_path: str, relative_path: str = "", review_status_filter: str = 'unreviewed') -> List[Dict[str, Any]]:
        """Get list of media files with metadata."""
        media_files = scan_media_files(root_path, relative_path)
        media_list = []
        
        for mf in media_files:
            # Read metadata to check review status
            metadata = MetadataReader.read_logical_metadata(mf['path'])
            review_status = metadata.get('reviewStatus', 'unreviewed')
            
            # Apply filter
            if review_status_filter == 'all':
                # Show all images
                media_list.append({
                    'path': mf['path'],
                    'relativePath': mf['relativePath'],
                    'filename': mf['filename'],
                    'reviewStatus': review_status
                })
            elif review_status_filter == 'reviewed':
                # Show only reviewed images
                if review_status == 'reviewed':
                    media_list.append({
                        'path': mf['path'],
                        'relativePath': mf['relativePath'],
                        'filename': mf['filename'],
                        'reviewStatus': review_status
                    })
            elif review_status_filter == 'unreviewed':
                # Show all images that are NOT reviewed (including those without status)
                if review_status != 'reviewed':
                    media_list.append({
                        'path': mf['path'],
                        'relativePath': mf['relativePath'],
                        'filename': mf['filename'],
                        'reviewStatus': review_status
                    })
                    'path': mf['path'],
                    'relativePath': mf['relativePath'],
                    'filename': mf['filename'],
                    'reviewStatus': review_status
                })
        
        return media_list
    
    @staticmethod
    def find_next_previous(
        root_path: str,
        current_relative_path: str,
        direction: str,
        review_status_filter: str = 'unreviewed'
    ) -> Optional[str]:
        """
        Find next or previous media item.
        
        Returns relative path of next/previous item, or None.
        """
        # Get all media in the same folder
        folder_path = '/'.join(current_relative_path.split('/')[:-1])
        media_list = MediaNavigator.get_media_list(root_path, folder_path, review_status_filter)
        
        # Find current index
        current_filename = current_relative_path.split('/')[-1]
        current_idx = None
        for i, item in enumerate(media_list):
            if item['relativePath'] == current_relative_path:
                current_idx = i
                break
        
        if current_idx is None:
            return None
        
        # Get next or previous
        if direction == 'next':
            if current_idx < len(media_list) - 1:
                return media_list[current_idx + 1]['relativePath']
        else:  # previous
            if current_idx > 0:
                return media_list[current_idx - 1]['relativePath']
        
        return None

