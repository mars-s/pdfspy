"""
Caching system for PDF extraction results.
Provides fast retrieval of previously processed documents.
"""
import joblib
import hashlib
from pathlib import Path
from functools import wraps
import json
import time
import os


class ExtractionCache:
    def __init__(self, cache_dir="cache/"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.max_cache_size_mb = 100  # Maximum cache size in MB
        self.max_age_days = 30  # Maximum age of cached items in days

    def _get_cache_key(self, pdf_path, interface_schema):
        """Generate cache key from PDF hash and interface"""
        pdf_hash = hashlib.md5(Path(pdf_path).read_bytes()).hexdigest()
        schema_hash = hashlib.md5(str(interface_schema).encode()).hexdigest()
        return f"{pdf_hash}_{schema_hash}.pkl"

    def _get_metadata(self):
        """Get cache metadata"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {}

    def _save_metadata(self, metadata):
        """Save cache metadata"""
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

    def _cleanup_cache(self):
        """Clean up old and large cache files"""
        metadata = self._get_metadata()
        current_time = time.time()
        total_size = 0
        files_to_remove = []

        # Check each cached file
        for cache_file in self.cache_dir.glob("*.pkl"):
            file_path = str(cache_file)
            file_size = cache_file.stat().st_size
            file_age_days = (current_time - cache_file.stat().st_mtime) / (24 * 3600)
            
            total_size += file_size
            
            # Mark for removal if too old
            if file_age_days > self.max_age_days:
                files_to_remove.append(cache_file)
                if file_path in metadata:
                    del metadata[file_path]

        # Remove old files
        for file_path in files_to_remove:
            try:
                file_path.unlink()
            except FileNotFoundError:
                pass

        # If cache is still too large, remove oldest files
        if total_size > self.max_cache_size_mb * 1024 * 1024:
            cache_files = [(f, f.stat().st_mtime) for f in self.cache_dir.glob("*.pkl")]
            cache_files.sort(key=lambda x: x[1])  # Sort by modification time
            
            for cache_file, _ in cache_files:
                if total_size <= self.max_cache_size_mb * 1024 * 1024:
                    break
                
                file_size = cache_file.stat().st_size
                total_size -= file_size
                
                try:
                    cache_file.unlink()
                    file_path = str(cache_file)
                    if file_path in metadata:
                        del metadata[file_path]
                except FileNotFoundError:
                    pass

        self._save_metadata(metadata)

    def get(self, pdf_path, interface_schema):
        """Get cached result"""
        cache_file = self.cache_dir / self._get_cache_key(pdf_path, interface_schema)
        
        if cache_file.exists():
            try:
                # Check if file is not too old
                file_age_days = (time.time() - cache_file.stat().st_mtime) / (24 * 3600)
                if file_age_days <= self.max_age_days:
                    result = joblib.load(cache_file)
                    
                    # Update metadata
                    metadata = self._get_metadata()
                    metadata[str(cache_file)] = {
                        'last_accessed': time.time(),
                        'pdf_path': str(pdf_path),
                        'hits': metadata.get(str(cache_file), {}).get('hits', 0) + 1
                    }
                    self._save_metadata(metadata)
                    
                    return result
                else:
                    # Remove old cache file
                    cache_file.unlink()
            except (FileNotFoundError, EOFError, joblib.externals.loky.process_executor.TerminatedWorkerError):
                pass
        
        return None

    def set(self, pdf_path, interface_schema, result):
        """Cache result"""
        # Clean up cache before adding new item
        self._cleanup_cache()
        
        cache_file = self.cache_dir / self._get_cache_key(pdf_path, interface_schema)
        
        try:
            joblib.dump(result, cache_file, compress=3)  # Use compression
            
            # Update metadata
            metadata = self._get_metadata()
            metadata[str(cache_file)] = {
                'created': time.time(),
                'pdf_path': str(pdf_path),
                'hits': 0,
                'size_bytes': cache_file.stat().st_size
            }
            self._save_metadata(metadata)
            
        except Exception as e:
            print(f"Warning: Failed to cache result: {e}")

    def get_cache_stats(self):
        """Get cache statistics"""
        metadata = self._get_metadata()
        cache_files = list(self.cache_dir.glob("*.pkl"))
        
        total_size = sum(f.stat().st_size for f in cache_files)
        total_hits = sum(item.get('hits', 0) for item in metadata.values())
        
        return {
            'total_files': len(cache_files),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'total_hits': total_hits,
            'average_hits_per_file': round(total_hits / len(cache_files), 2) if cache_files else 0,
            'cache_dir': str(self.cache_dir)
        }

    def clear_cache(self):
        """Clear all cache files"""
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                cache_file.unlink()
            except FileNotFoundError:
                pass
        
        if self.metadata_file.exists():
            self.metadata_file.unlink()


def cached_extraction(cache_dir="cache/"):
    """Decorator for caching extraction results"""
    cache = ExtractionCache(cache_dir)

    def decorator(func):
        @wraps(func)
        def wrapper(pdf_path, interface_schema, *args, **kwargs):
            # Try cache first
            cached_result = cache.get(pdf_path, interface_schema)
            if cached_result:
                return cached_result

            # Compute and cache result
            result = func(pdf_path, interface_schema, *args, **kwargs)
            cache.set(pdf_path, interface_schema, result)
            return result

        return wrapper
    return decorator


def with_cache_stats(func):
    """Decorator to print cache statistics after function execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        cache = ExtractionCache()
        
        # Execute function
        result = func(*args, **kwargs)
        
        # Print cache stats
        stats = cache.get_cache_stats()
        print(f"\nCache Statistics:")
        print(f"  Files: {stats['total_files']}")
        print(f"  Size: {stats['total_size_mb']} MB")
        print(f"  Total hits: {stats['total_hits']}")
        print(f"  Avg hits/file: {stats['average_hits_per_file']}")
        
        return result
    return wrapper
