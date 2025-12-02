"""Background worker for generating thumbnails asynchronously."""
import os
import threading
import queue
import logging
from typing import Optional
from backend.media.preview_generator import PreviewGenerator

logger = logging.getLogger(__name__)


class ThumbnailWorker:
    """Background worker that processes thumbnail generation tasks."""
    
    def __init__(self, thumbnail_cache_root: str, max_workers: int = 2):
        self.thumbnail_cache_root = thumbnail_cache_root
        self.max_workers = max_workers
        self.task_queue = queue.Queue()
        self.workers = []
        self.running = False
        self.preview_gen = PreviewGenerator(thumbnail_cache_root)
    
    def start(self):
        """Start the worker threads."""
        if self.running:
            return
        
        self.running = True
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker_loop, daemon=True, name=f"ThumbnailWorker-{i}")
            worker.start()
            self.workers.append(worker)
        logger.info(f"Started {self.max_workers} thumbnail worker threads")
    
    def stop(self):
        """Stop the worker threads."""
        self.running = False
        # Add None sentinels to wake up workers
        for _ in range(self.max_workers):
            self.task_queue.put(None)
        for worker in self.workers:
            worker.join(timeout=5)
        self.workers.clear()
        logger.info("Stopped thumbnail worker threads")
    
    def queue_thumbnail(self, media_path: str, is_image: bool = True):
        """Queue a thumbnail generation task."""
        if not os.path.exists(media_path):
            logger.warning(f"Cannot queue thumbnail for non-existent file: {media_path}")
            return
        
        # Check if thumbnail already exists
        cache_path = self.preview_gen._get_cache_path(media_path, 'thumb')
        if os.path.exists(cache_path):
            logger.debug(f"Thumbnail already exists for {media_path}, skipping")
            return
        
        self.task_queue.put({
            'media_path': media_path,
            'is_image': is_image
        })
        logger.debug(f"Queued thumbnail generation for {media_path}")
    
    def _worker_loop(self):
        """Worker thread loop."""
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                if task is None:  # Sentinel to stop
                    break
                
                media_path = task['media_path']
                is_image = task['is_image']
                
                try:
                    if is_image:
                        self.preview_gen.generate_image_thumbnail(media_path)
                    else:
                        self.preview_gen.generate_video_thumbnail(media_path)
                    logger.info(f"Generated thumbnail for {media_path}")
                except Exception as e:
                    logger.error(f"Failed to generate thumbnail for {media_path}: {e}", exc_info=True)
                finally:
                    self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in thumbnail worker: {e}", exc_info=True)
    
    def get_queue_size(self) -> int:
        """Get the number of pending tasks."""
        return self.task_queue.qsize()


# Global worker instance
_global_worker: Optional[ThumbnailWorker] = None


def get_thumbnail_worker(thumbnail_cache_root: str = None) -> ThumbnailWorker:
    """Get or create the global thumbnail worker instance."""
    global _global_worker
    if _global_worker is None:
        if thumbnail_cache_root is None:
            raise ValueError("thumbnail_cache_root must be provided for first call")
        _global_worker = ThumbnailWorker(thumbnail_cache_root)
        _global_worker.start()
    return _global_worker


def queue_thumbnail_generation(media_path: str, is_image: bool = True, thumbnail_cache_root: str = None):
    """Queue a thumbnail generation task (convenience function)."""
    worker = get_thumbnail_worker(thumbnail_cache_root)
    worker.queue_thumbnail(media_path, is_image)


