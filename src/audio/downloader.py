"""
Audio download module using yt-dlp.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import yt_dlp
from loguru import logger
import hashlib


class AudioDownloader:
    """Downloads and processes podcast audio files."""

    def __init__(self, output_dir: str, audio_format: str = "mp3", quality: str = "good"):
        """
        Initialize the audio downloader.

        Args:
            output_dir: Directory to save downloaded audio files
            audio_format: Audio format (mp3, m4a, wav)
            quality: Audio quality (best, good, medium)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.audio_format = audio_format
        self.quality = quality

    def _get_quality_params(self) -> str:
        """Get ffmpeg audio quality parameters based on quality setting."""
        quality_map = {
            "best": "0",      # VBR 220-260 kbps
            "good": "2",      # VBR 170-210 kbps
            "medium": "5"     # VBR 120-150 kbps
        }
        return quality_map.get(self.quality, "2")

    def _generate_filename(self, episode_id: int, title: str) -> str:
        """
        Generate a safe filename for the audio file.

        Args:
            episode_id: Episode ID
            title: Episode title

        Returns:
            Safe filename
        """
        # Create a hash of the title to avoid filesystem issues with long/special chars
        title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
        safe_title = "".join(c for c in title[:50] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')
        return f"{episode_id}_{safe_title}_{title_hash}.{self.audio_format}"

    def download(
        self,
        url: str,
        episode_id: int,
        title: str,
        progress_callback: Optional[callable] = None
    ) -> Optional[str]:
        """
        Download audio from URL.

        Args:
            url: Audio URL
            episode_id: Episode ID for filename
            title: Episode title
            progress_callback: Optional callback for progress updates

        Returns:
            Path to downloaded file, or None if download failed
        """
        filename = self._generate_filename(episode_id, title)
        output_path = self.output_dir / filename

        # If file already exists, return it
        if output_path.exists():
            logger.info(f"Audio file already exists: {output_path}")
            return str(output_path)

        # yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(output_path.with_suffix('')),  # yt-dlp adds extension
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.audio_format,
                'preferredquality': self._get_quality_params(),
            }],
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

        # Add progress hook if callback provided
        if progress_callback:
            ydl_opts['progress_hooks'] = [progress_callback]

        try:
            logger.info(f"Downloading audio from {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # yt-dlp may have added the extension, so find the file
            if output_path.exists():
                logger.info(f"Audio downloaded successfully: {output_path}")
                return str(output_path)
            else:
                # Sometimes yt-dlp creates files with different extensions
                for ext in ['.mp3', '.m4a', '.webm', '.opus']:
                    alt_path = output_path.with_suffix(ext)
                    if alt_path.exists():
                        logger.info(f"Audio downloaded successfully: {alt_path}")
                        return str(alt_path)

                logger.error(f"Download completed but file not found: {output_path}")
                return None

        except Exception as e:
            logger.error(f"Failed to download audio from {url}: {e}")
            return None

    def get_audio_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get audio metadata without downloading.

        Args:
            url: Audio URL

        Returns:
            Dictionary with audio metadata
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'description': info.get('description'),
                    'upload_date': info.get('upload_date'),
                    'uploader': info.get('uploader'),
                }
        except Exception as e:
            logger.error(f"Failed to extract audio info from {url}: {e}")
            return None

    def delete_audio(self, file_path: str) -> bool:
        """
        Delete an audio file.

        Args:
            file_path: Path to audio file

        Returns:
            True if deleted successfully
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"Deleted audio file: {file_path}")
                return True
            else:
                logger.warning(f"Audio file not found: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete audio file {file_path}: {e}")
            return False

    def get_file_size(self, file_path: str) -> Optional[int]:
        """Get size of audio file in bytes."""
        try:
            return Path(file_path).stat().st_size
        except Exception:
            return None
