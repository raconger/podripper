"""
Transcription module using OpenAI Whisper.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import whisper
import torch
from loguru import logger


class WhisperTranscriber:
    """Transcribe audio using OpenAI Whisper."""

    def __init__(
        self,
        model_name: str = "base",
        device: Optional[str] = None,
        language: Optional[str] = None
    ):
        """
        Initialize the transcriber.

        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
            device: Device to use (cuda, cpu). Auto-detect if None
            language: Language code (e.g., 'en'). Auto-detect if None
        """
        self.model_name = model_name
        self.language = language

        # Determine device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Loading Whisper model '{model_name}' on device '{self.device}'")
        self.model = whisper.load_model(model_name, device=self.device)
        logger.info("Whisper model loaded successfully")

    def transcribe(
        self,
        audio_path: str,
        temperature: float = 0.0,
        word_timestamps: bool = False,
        progress_callback: Optional[callable] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to audio file
            temperature: Temperature for sampling (0 = deterministic)
            word_timestamps: Whether to include word-level timestamps
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with transcription results
        """
        if not Path(audio_path).exists():
            logger.error(f"Audio file not found: {audio_path}")
            return None

        try:
            logger.info(f"Transcribing audio file: {audio_path}")

            # Transcribe options
            options = {
                'language': self.language,
                'temperature': temperature,
                'word_timestamps': word_timestamps,
                'verbose': False,
            }

            # Remove None values
            options = {k: v for k, v in options.items() if v is not None}

            result = self.model.transcribe(audio_path, **options)

            # Extract relevant information
            transcription_result = {
                'text': result['text'].strip(),
                'language': result['language'],
                'segments': [],
            }

            # Process segments
            for segment in result.get('segments', []):
                segment_data = {
                    'id': segment['id'],
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'].strip(),
                }

                # Add word-level timestamps if available
                if word_timestamps and 'words' in segment:
                    segment_data['words'] = segment['words']

                transcription_result['segments'].append(segment_data)

            logger.info(f"Transcription completed. Length: {len(result['text'])} characters")

            return transcription_result

        except Exception as e:
            logger.error(f"Transcription failed for {audio_path}: {e}")
            return None

    def transcribe_to_text(
        self,
        audio_path: str,
        output_path: Optional[str] = None,
        include_timestamps: bool = True
    ) -> Optional[str]:
        """
        Transcribe audio and return or save as formatted text.

        Args:
            audio_path: Path to audio file
            output_path: Optional path to save transcription
            include_timestamps: Whether to include segment timestamps

        Returns:
            Transcription text
        """
        result = self.transcribe(audio_path)

        if not result:
            return None

        # Format text
        if include_timestamps and result.get('segments'):
            lines = []
            for segment in result['segments']:
                timestamp = self._format_timestamp(segment['start'])
                lines.append(f"[{timestamp}] {segment['text']}")
            formatted_text = "\n".join(lines)
        else:
            formatted_text = result['text']

        # Save if output path provided
        if output_path:
            try:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(formatted_text, encoding='utf-8')
                logger.info(f"Transcription saved to: {output_path}")
            except Exception as e:
                logger.error(f"Failed to save transcription to {output_path}: {e}")

        return formatted_text

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Format seconds as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def get_model_info(self) -> Dict[str, str]:
        """Get information about the loaded model."""
        return {
            'model_name': self.model_name,
            'device': self.device,
            'language': self.language or 'auto-detect',
        }


class OpenAITranscriber:
    """Transcribe audio using OpenAI's API (cloud-based)."""

    def __init__(self, api_key: str, model: str = "whisper-1"):
        """
        Initialize OpenAI transcriber.

        Args:
            api_key: OpenAI API key
            model: Model name (default: whisper-1)
        """
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
        logger.info(f"Initialized OpenAI transcriber with model: {model}")

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        temperature: float = 0.0
    ) -> Optional[Dict[str, Any]]:
        """
        Transcribe using OpenAI API.

        Args:
            audio_path: Path to audio file
            language: Language code (optional)
            temperature: Temperature for sampling

        Returns:
            Dictionary with transcription results
        """
        if not Path(audio_path).exists():
            logger.error(f"Audio file not found: {audio_path}")
            return None

        try:
            logger.info(f"Transcribing with OpenAI API: {audio_path}")

            with open(audio_path, 'rb') as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=language,
                    temperature=temperature,
                    response_format="verbose_json"
                )

            result = {
                'text': response.text.strip(),
                'language': response.language,
                'segments': []
            }

            # Process segments if available
            if hasattr(response, 'segments') and response.segments:
                for segment in response.segments:
                    result['segments'].append({
                        'id': segment.id,
                        'start': segment.start,
                        'end': segment.end,
                        'text': segment.text.strip(),
                    })

            logger.info(f"OpenAI transcription completed. Length: {len(response.text)} characters")
            return result

        except Exception as e:
            logger.error(f"OpenAI transcription failed for {audio_path}: {e}")
            return None

    def transcribe_to_text(
        self,
        audio_path: str,
        output_path: Optional[str] = None,
        include_timestamps: bool = True
    ) -> Optional[str]:
        """
        Transcribe audio and return or save as formatted text.

        Args:
            audio_path: Path to audio file
            output_path: Optional path to save transcription
            include_timestamps: Whether to include segment timestamps

        Returns:
            Transcription text
        """
        result = self.transcribe(audio_path)

        if not result:
            return None

        # Format text
        if include_timestamps and result.get('segments'):
            lines = []
            for segment in result['segments']:
                timestamp = WhisperTranscriber._format_timestamp(segment['start'])
                lines.append(f"[{timestamp}] {segment['text']}")
            formatted_text = "\n".join(lines)
        else:
            formatted_text = result['text']

        # Save if output path provided
        if output_path:
            try:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(formatted_text, encoding='utf-8')
                logger.info(f"Transcription saved to: {output_path}")
            except Exception as e:
                logger.error(f"Failed to save transcription to {output_path}: {e}")

        return formatted_text
