"""
Transcript cleaning module using LLMs.
"""

from typing import Optional, List
from pathlib import Path
from loguru import logger
import anthropic
from openai import OpenAI


CLEANING_PROMPT = """You're a transcript editor. Clean up this podcast transcript while preserving all the content.

Guidelines:
- Keep the same length and all information
- Remove filler words like "um", "uh", "ah", "like" (when used as filler), "you know"
- Fix obvious transcription errors
- Preserve all technical conversations and terminology
- Maintain the conversational tone
- Keep all names, companies, and specific references
- Do NOT summarize or shorten the content
- Do NOT add information that wasn't in the original

Here's the transcript to clean:

{transcript}"""


class TranscriptCleaner:
    """Clean transcripts using LLM APIs."""

    def __init__(
        self,
        provider: str = "anthropic",
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4000
    ):
        """
        Initialize the transcript cleaner.

        Args:
            provider: LLM provider (anthropic, openai, ollama)
            model: Model name
            api_key: API key for cloud providers
            base_url: Base URL for Ollama
            temperature: Sampling temperature
            max_tokens: Maximum tokens per request
        """
        self.provider = provider.lower()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize client based on provider
        if self.provider == "anthropic":
            if not api_key:
                raise ValueError("API key required for Anthropic")
            self.client = anthropic.Anthropic(api_key=api_key)
            logger.info(f"Initialized Anthropic cleaner with model: {model}")

        elif self.provider == "openai":
            if not api_key:
                raise ValueError("API key required for OpenAI")
            self.client = OpenAI(api_key=api_key)
            logger.info(f"Initialized OpenAI cleaner with model: {model}")

        elif self.provider == "ollama":
            base_url = base_url or "http://localhost:11434"
            self.client = OpenAI(base_url=f"{base_url}/v1", api_key="ollama")
            logger.info(f"Initialized Ollama cleaner with model: {model}")

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def clean_transcript(
        self,
        transcript: str,
        chunk_size: int = 15000
    ) -> Optional[str]:
        """
        Clean a transcript using the LLM.

        Args:
            transcript: Raw transcript text
            chunk_size: Maximum characters per chunk (for long transcripts)

        Returns:
            Cleaned transcript
        """
        if not transcript or not transcript.strip():
            logger.warning("Empty transcript provided")
            return transcript

        # For long transcripts, process in chunks
        if len(transcript) > chunk_size:
            logger.info(f"Transcript is long ({len(transcript)} chars), processing in chunks")
            return self._clean_transcript_chunked(transcript, chunk_size)
        else:
            return self._clean_transcript_single(transcript)

    def _clean_transcript_single(self, transcript: str) -> Optional[str]:
        """Clean a single transcript (not chunked)."""
        try:
            prompt = CLEANING_PROMPT.format(transcript=transcript)

            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                cleaned_text = response.content[0].text

            elif self.provider in ["openai", "ollama"]:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                cleaned_text = response.choices[0].message.content

            else:
                logger.error(f"Unsupported provider: {self.provider}")
                return None

            logger.info(f"Transcript cleaned successfully. Original: {len(transcript)} chars, Cleaned: {len(cleaned_text)} chars")
            return cleaned_text.strip()

        except Exception as e:
            logger.error(f"Failed to clean transcript: {e}")
            return None

    def _clean_transcript_chunked(self, transcript: str, chunk_size: int) -> Optional[str]:
        """
        Clean a long transcript by splitting into chunks.

        Args:
            transcript: Full transcript
            chunk_size: Size of each chunk

        Returns:
            Cleaned transcript
        """
        # Split into sentences (simple approach)
        sentences = transcript.replace('\n', ' ').split('. ')

        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence_size = len(sentence)

            if current_size + sentence_size > chunk_size and current_chunk:
                # Save current chunk and start new one
                chunks.append('. '.join(current_chunk) + '.')
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size

        # Add remaining chunk
        if current_chunk:
            chunks.append('. '.join(current_chunk))

        logger.info(f"Split transcript into {len(chunks)} chunks")

        # Clean each chunk
        cleaned_chunks = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Cleaning chunk {i + 1}/{len(chunks)}")
            cleaned = self._clean_transcript_single(chunk)
            if cleaned:
                cleaned_chunks.append(cleaned)
            else:
                logger.warning(f"Failed to clean chunk {i + 1}, using original")
                cleaned_chunks.append(chunk)

        # Combine cleaned chunks
        return '\n\n'.join(cleaned_chunks)

    def clean_transcript_file(
        self,
        input_path: str,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Clean a transcript from a file.

        Args:
            input_path: Path to input transcript file
            output_path: Optional path to save cleaned transcript

        Returns:
            Cleaned transcript text
        """
        try:
            # Read input file
            input_file = Path(input_path)
            if not input_file.exists():
                logger.error(f"Input file not found: {input_path}")
                return None

            raw_transcript = input_file.read_text(encoding='utf-8')

            # Clean transcript
            cleaned_transcript = self.clean_transcript(raw_transcript)

            if not cleaned_transcript:
                return None

            # Save to output file if specified
            if output_path:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(cleaned_transcript, encoding='utf-8')
                logger.info(f"Cleaned transcript saved to: {output_path}")

            return cleaned_transcript

        except Exception as e:
            logger.error(f"Failed to process transcript file {input_path}: {e}")
            return None

    def get_cleaner_info(self) -> dict:
        """Get information about the cleaner configuration."""
        return {
            'provider': self.provider,
            'model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }
