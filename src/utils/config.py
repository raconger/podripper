"""
Configuration management for podcast processing system.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from loguru import logger


class FeedConfig(BaseModel):
    """Configuration for a podcast feed."""
    name: str
    url: str
    enabled: bool = True


class ProcessingConfig(BaseModel):
    """Processing settings."""
    max_episodes_per_run: int = 5
    newest_first: bool = True
    max_age_days: int = 0
    concurrent_workers: int = 1


class AudioConfig(BaseModel):
    """Audio settings."""
    format: str = "mp3"
    quality: str = "good"
    delete_after_transcription: bool = False


class TranscriptionConfig(BaseModel):
    """Transcription settings."""
    language: Optional[str] = None
    word_timestamps: bool = False
    temperature: float = 0.0


class CleaningConfig(BaseModel):
    """Transcript cleaning settings."""
    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.3
    max_tokens: int = 4000


class SummarizationConfig(BaseModel):
    """Summarization settings."""
    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.5
    max_tokens: int = 4000
    output_format: str = "both"  # json, markdown, both


class ScheduleConfig(BaseModel):
    """Schedule settings."""
    enabled: bool = False
    cron: str = "0 2 * * *"


class Config(BaseModel):
    """Main configuration."""
    feeds: list[FeedConfig] = Field(default_factory=list)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
    cleaning: CleaningConfig = Field(default_factory=CleaningConfig)
    summarization: SummarizationConfig = Field(default_factory=SummarizationConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)


class ConfigManager:
    """Manages configuration loading and environment variables."""

    def __init__(self, config_path: Optional[str] = None, env_path: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to YAML config file
            env_path: Path to .env file
        """
        # Load environment variables
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()  # Load from default .env location

        # Load config file
        self.config_path = Path(config_path) if config_path else Path("config.yaml")
        self.config = self._load_config()

        # Load environment-specific settings
        self.env = self._load_env_vars()

    def _load_config(self) -> Config:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}. Using defaults.")
            return Config()

        try:
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)

            config = Config(**config_data)
            logger.info(f"Configuration loaded from: {self.config_path}")
            return config

        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            logger.info("Using default configuration")
            return Config()

    def _load_env_vars(self) -> Dict[str, Any]:
        """Load environment variables."""
        return {
            # API Keys
            'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY'),
            'openai_api_key': os.getenv('OPENAI_API_KEY'),

            # LLM Provider
            'llm_provider': os.getenv('LLM_PROVIDER', 'anthropic'),

            # Ollama
            'ollama_base_url': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
            'ollama_model': os.getenv('OLLAMA_MODEL', 'llama3'),

            # Transcription
            'transcription_provider': os.getenv('TRANSCRIPTION_PROVIDER', 'whisper'),
            'whisper_model': os.getenv('WHISPER_MODEL', 'base'),

            # Paths
            'database_path': os.getenv('DATABASE_PATH', 'data/podcasts.duckdb'),
            'audio_dir': os.getenv('AUDIO_DIR', 'data/audio'),
            'transcripts_dir': os.getenv('TRANSCRIPTS_DIR', 'data/transcripts'),
            'summaries_dir': os.getenv('SUMMARIES_DIR', 'data/summaries'),

            # Logging
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'log_file': os.getenv('LOG_FILE', 'data/podripper.log'),
        }

    def get_llm_api_key(self, provider: Optional[str] = None) -> Optional[str]:
        """Get API key for specified LLM provider."""
        provider = provider or self.env['llm_provider']

        if provider == 'anthropic':
            return self.env['anthropic_api_key']
        elif provider == 'openai':
            return self.env['openai_api_key']
        elif provider == 'ollama':
            return None  # Ollama doesn't need an API key
        else:
            logger.warning(f"Unknown provider: {provider}")
            return None

    def get_database_path(self) -> str:
        """Get database path."""
        return self.env['database_path']

    def get_audio_dir(self) -> str:
        """Get audio directory."""
        return self.env['audio_dir']

    def get_transcripts_dir(self) -> str:
        """Get transcripts directory."""
        return self.env['transcripts_dir']

    def get_summaries_dir(self) -> str:
        """Get summaries directory."""
        return self.env['summaries_dir']

    def get_enabled_feeds(self) -> list[FeedConfig]:
        """Get list of enabled feeds."""
        return [feed for feed in self.config.feeds if feed.enabled]

    def save_config(self, path: Optional[str] = None):
        """Save current configuration to file."""
        save_path = Path(path) if path else self.config_path

        try:
            with open(save_path, 'w') as f:
                yaml.dump(
                    self.config.model_dump(),
                    f,
                    default_flow_style=False,
                    sort_keys=False
                )
            logger.info(f"Configuration saved to: {save_path}")

        except Exception as e:
            logger.error(f"Failed to save config to {save_path}: {e}")
