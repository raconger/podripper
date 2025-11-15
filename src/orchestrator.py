"""
Main orchestrator for podcast processing pipeline.
"""

import json
from pathlib import Path
from typing import Optional
from loguru import logger

from .database import DatabaseManager
from .audio import AudioDownloader, FeedParser
from .transcription import WhisperTranscriber, OpenAITranscriber
from .cleaning import TranscriptCleaner
from .summarization import PodcastSummarizer
from .utils import ConfigManager


class PodcastOrchestrator:
    """Orchestrates the complete podcast processing pipeline."""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the orchestrator.

        Args:
            config_manager: Configuration manager instance
        """
        self.config = config_manager
        self.db = DatabaseManager(config_manager.get_database_path())

        # Initialize components
        self._init_components()

    def _init_components(self):
        """Initialize all processing components."""
        # Audio downloader
        self.audio_downloader = AudioDownloader(
            output_dir=self.config.get_audio_dir(),
            audio_format=self.config.config.audio.format,
            quality=self.config.config.audio.quality
        )

        # Transcriber
        transcription_provider = self.config.env['transcription_provider']

        if transcription_provider == 'whisper':
            self.transcriber = WhisperTranscriber(
                model_name=self.config.env['whisper_model'],
                language=self.config.config.transcription.language
            )
        elif transcription_provider == 'openai':
            api_key = self.config.env['openai_api_key']
            self.transcriber = OpenAITranscriber(api_key=api_key)
        else:
            raise ValueError(f"Unsupported transcription provider: {transcription_provider}")

        # Transcript cleaner
        llm_provider = self.config.env['llm_provider']
        api_key = self.config.get_llm_api_key(llm_provider)

        self.cleaner = TranscriptCleaner(
            provider=llm_provider,
            model=self.config.config.cleaning.model,
            api_key=api_key,
            base_url=self.config.env['ollama_base_url'],
            temperature=self.config.config.cleaning.temperature,
            max_tokens=self.config.config.cleaning.max_tokens
        )

        # Summarizer
        self.summarizer = PodcastSummarizer(
            provider=llm_provider,
            model=self.config.config.summarization.model,
            api_key=api_key,
            base_url=self.config.env['ollama_base_url'],
            temperature=self.config.config.summarization.temperature,
            max_tokens=self.config.config.summarization.max_tokens
        )

        logger.info("All components initialized successfully")

    def sync_feeds(self):
        """Sync all enabled feeds and add new episodes to database."""
        logger.info("Starting feed synchronization")

        enabled_feeds = self.config.get_enabled_feeds()
        logger.info(f"Found {len(enabled_feeds)} enabled feeds")

        total_new_episodes = 0

        for feed_config in enabled_feeds:
            logger.info(f"Processing feed: {feed_config.name}")

            # Add or update feed in database
            feed_id = self.db.add_feed(
                name=feed_config.name,
                url=feed_config.url,
                enabled=feed_config.enabled
            )

            # Get existing episode GUIDs from database
            with self.db.get_connection() as conn:
                existing_guids = conn.execute(
                    "SELECT guid FROM episodes WHERE feed_id = ?",
                    [feed_id]
                ).fetchall()
                existing_guids = [g[0] for g in existing_guids]

            # Parse feed and get new episodes
            new_episodes = FeedParser.get_new_episodes(
                url=feed_config.url,
                existing_guids=existing_guids,
                max_age_days=self.config.config.processing.max_age_days or None
            )

            logger.info(f"Found {len(new_episodes)} new episodes for {feed_config.name}")

            # Add new episodes to database
            for episode in new_episodes:
                episode_id = self.db.add_episode(
                    feed_id=feed_id,
                    title=episode['title'],
                    audio_url=episode['audio_url'],
                    guid=episode['guid'],
                    description=episode.get('description'),
                    published_date=episode.get('published_date'),
                    duration_seconds=episode.get('duration_seconds')
                )

                if episode_id:
                    logger.info(f"Added episode: {episode['title']}")
                    total_new_episodes += 1

            # Update last checked timestamp
            self.db.update_feed_checked(feed_id)

        logger.info(f"Feed synchronization completed. Added {total_new_episodes} new episodes")
        return total_new_episodes

    def process_episode(self, episode_id: int) -> bool:
        """
        Process a single episode through the complete pipeline.

        Args:
            episode_id: Episode ID

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Processing episode ID: {episode_id}")

        try:
            # Get episode info
            with self.db.get_connection() as conn:
                episode = conn.execute(
                    "SELECT id, title, audio_url FROM episodes WHERE id = ?",
                    [episode_id]
                ).fetchone()

                if not episode:
                    logger.error(f"Episode not found: {episode_id}")
                    return False

                ep_id, title, audio_url = episode

            # Step 1: Download audio
            logger.info(f"Step 1/4: Downloading audio for '{title}'")
            self.db.update_status(episode_id, "downloading")
            self.db.log_processing(episode_id, "download", "started")

            audio_path = self.audio_downloader.download(
                url=audio_url,
                episode_id=episode_id,
                title=title
            )

            if not audio_path:
                self.db.update_status(episode_id, "failed", error_message="Audio download failed")
                self.db.log_processing(episode_id, "download", "error", "Download failed")
                return False

            self.db.update_status(episode_id, "downloading", audio_path=audio_path)
            self.db.log_processing(episode_id, "download", "success", f"Downloaded to {audio_path}")

            # Step 2: Transcribe
            logger.info(f"Step 2/4: Transcribing audio for '{title}'")
            self.db.update_status(episode_id, "transcribing")
            self.db.log_processing(episode_id, "transcribe", "started")

            # Create transcript path
            transcript_dir = Path(self.config.get_transcripts_dir())
            transcript_dir.mkdir(parents=True, exist_ok=True)
            raw_transcript_path = transcript_dir / f"{episode_id}_raw.txt"

            raw_transcript = self.transcriber.transcribe_to_text(
                audio_path=audio_path,
                output_path=str(raw_transcript_path),
                include_timestamps=False
            )

            if not raw_transcript:
                self.db.update_status(episode_id, "failed", error_message="Transcription failed")
                self.db.log_processing(episode_id, "transcribe", "error", "Transcription failed")
                return False

            # Save to database
            model_name = self.transcriber.model_name if hasattr(self.transcriber, 'model_name') else 'openai-whisper'
            self.db.save_transcript(
                episode_id=episode_id,
                raw_text=raw_transcript,
                transcription_model=model_name
            )
            self.db.update_status(episode_id, "transcribing", raw_transcript_path=str(raw_transcript_path))
            self.db.log_processing(episode_id, "transcribe", "success", f"Transcribed {len(raw_transcript)} characters")

            # Delete audio if configured
            if self.config.config.audio.delete_after_transcription:
                self.audio_downloader.delete_audio(audio_path)

            # Step 3: Clean transcript
            logger.info(f"Step 3/4: Cleaning transcript for '{title}'")
            self.db.update_status(episode_id, "cleaning")
            self.db.log_processing(episode_id, "clean", "started")

            cleaned_transcript = self.cleaner.clean_transcript(raw_transcript)

            if not cleaned_transcript:
                logger.warning("Transcript cleaning failed, using raw transcript")
                cleaned_transcript = raw_transcript

            # Save cleaned transcript
            cleaned_transcript_path = transcript_dir / f"{episode_id}_cleaned.txt"
            cleaned_transcript_path.write_text(cleaned_transcript, encoding='utf-8')

            self.db.save_transcript(
                episode_id=episode_id,
                cleaned_text=cleaned_transcript,
                cleaning_model=self.cleaner.model
            )
            self.db.update_status(episode_id, "cleaning", cleaned_transcript_path=str(cleaned_transcript_path))
            self.db.log_processing(episode_id, "clean", "success", f"Cleaned {len(cleaned_transcript)} characters")

            # Step 4: Generate summary
            logger.info(f"Step 4/4: Generating summary for '{title}'")
            self.db.update_status(episode_id, "summarizing")
            self.db.log_processing(episode_id, "summarize", "started")

            summary_data = self.summarizer.summarize(cleaned_transcript)

            if not summary_data:
                self.db.update_status(episode_id, "failed", error_message="Summarization failed")
                self.db.log_processing(episode_id, "summarize", "error", "Summarization failed")
                return False

            # Save summary files
            summary_dir = Path(self.config.get_summaries_dir())
            summary_dir.mkdir(parents=True, exist_ok=True)

            output_format = self.config.config.summarization.output_format

            # Save JSON
            if output_format in ["json", "both"]:
                json_path = summary_dir / f"{episode_id}_summary.json"
                json_path.write_text(
                    json.dumps(summary_data, indent=2, ensure_ascii=False),
                    encoding='utf-8'
                )

            # Save Markdown
            markdown_path = None
            if output_format in ["markdown", "both"]:
                markdown_text = self.summarizer.summarize_to_markdown(cleaned_transcript)
                if markdown_text:
                    markdown_path = summary_dir / f"{episode_id}_summary.md"
                    markdown_path.write_text(markdown_text, encoding='utf-8')

            # Save to database
            summary_path = str(markdown_path or json_path)
            self.db.save_summary(
                episode_id=episode_id,
                summary_data={
                    'host_and_guest': summary_data.get('host_and_guest'),
                    'comprehensive_summary': summary_data.get('comprehensive_summary'),
                    'key_topics': json.dumps(summary_data.get('key_topics', [])),
                    'actionable_quotes': json.dumps(summary_data.get('actionable_quotes', [])),
                    'investment_theses': json.dumps(summary_data.get('investment_theses', [])),
                    'noteworthy_observations': json.dumps(summary_data.get('noteworthy_observations', [])),
                    'company_mentions': json.dumps(summary_data.get('company_mentions', []))
                },
                model_used=self.summarizer.model
            )

            self.db.update_status(episode_id, "completed", summary_path=summary_path)
            self.db.log_processing(episode_id, "summarize", "success", f"Summary saved to {summary_path}")

            logger.info(f"Episode '{title}' processed successfully!")
            return True

        except Exception as e:
            logger.error(f"Failed to process episode {episode_id}: {e}")
            self.db.update_status(episode_id, "failed", error_message=str(e))
            self.db.log_processing(episode_id, "process", "error", str(e))
            return False

    def process_pending_episodes(self, limit: Optional[int] = None):
        """
        Process all pending episodes.

        Args:
            limit: Maximum number of episodes to process
        """
        limit = limit or self.config.config.processing.max_episodes_per_run

        logger.info(f"Processing up to {limit} pending episodes")

        pending_episodes = self.db.get_pending_episodes(limit=limit)

        if not pending_episodes:
            logger.info("No pending episodes to process")
            return

        logger.info(f"Found {len(pending_episodes)} pending episodes")

        success_count = 0
        failed_count = 0

        for episode in pending_episodes:
            success = self.process_episode(episode['id'])

            if success:
                success_count += 1
            else:
                failed_count += 1

        logger.info(f"Processing completed. Success: {success_count}, Failed: {failed_count}")

    def get_stats(self):
        """Get processing statistics."""
        return self.db.get_processing_stats()
