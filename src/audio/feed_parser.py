"""
RSS feed parser for podcasts.
"""

import feedparser
from typing import List, Dict, Any, Optional
from datetime import datetime
from dateutil import parser as date_parser
from loguru import logger


class FeedParser:
    """Parse podcast RSS feeds."""

    @staticmethod
    def parse_feed(url: str) -> Optional[Dict[str, Any]]:
        """
        Parse a podcast RSS feed.

        Args:
            url: RSS feed URL

        Returns:
            Dictionary with feed info and episodes
        """
        try:
            logger.info(f"Parsing feed: {url}")
            feed = feedparser.parse(url)

            if feed.bozo:
                logger.warning(f"Feed has parsing issues: {url}")

            # Extract feed information
            feed_info = {
                'title': feed.feed.get('title', 'Unknown'),
                'description': feed.feed.get('description', ''),
                'link': feed.feed.get('link', ''),
                'language': feed.feed.get('language', ''),
            }

            # Parse episodes
            episodes = []
            for entry in feed.entries:
                episode = FeedParser._parse_episode(entry)
                if episode:
                    episodes.append(episode)

            logger.info(f"Found {len(episodes)} episodes in feed: {feed_info['title']}")

            return {
                'feed_info': feed_info,
                'episodes': episodes
            }

        except Exception as e:
            logger.error(f"Failed to parse feed {url}: {e}")
            return None

    @staticmethod
    def _parse_episode(entry: Any) -> Optional[Dict[str, Any]]:
        """
        Parse a single episode from feed entry.

        Args:
            entry: Feed entry object

        Returns:
            Dictionary with episode information
        """
        try:
            # Get audio URL from enclosures
            audio_url = None
            for enclosure in entry.get('enclosures', []):
                if 'audio' in enclosure.get('type', ''):
                    audio_url = enclosure.get('href')
                    break

            # If no enclosure, try links
            if not audio_url:
                for link in entry.get('links', []):
                    if 'audio' in link.get('type', ''):
                        audio_url = link.get('href')
                        break

            if not audio_url:
                logger.warning(f"No audio URL found for episode: {entry.get('title')}")
                return None

            # Parse published date
            published_date = None
            if 'published_parsed' in entry and entry.published_parsed:
                published_date = datetime(*entry.published_parsed[:6])
            elif 'published' in entry:
                try:
                    published_date = date_parser.parse(entry.published)
                except Exception:
                    pass

            # Get duration if available (iTunes extension)
            duration_seconds = None
            if 'itunes_duration' in entry:
                duration_str = entry.itunes_duration
                try:
                    # Parse duration (can be seconds or HH:MM:SS)
                    if ':' in duration_str:
                        parts = duration_str.split(':')
                        if len(parts) == 3:
                            h, m, s = map(int, parts)
                            duration_seconds = h * 3600 + m * 60 + s
                        elif len(parts) == 2:
                            m, s = map(int, parts)
                            duration_seconds = m * 60 + s
                    else:
                        duration_seconds = int(duration_str)
                except Exception:
                    pass

            return {
                'title': entry.get('title', 'Untitled'),
                'description': entry.get('summary', ''),
                'audio_url': audio_url,
                'published_date': published_date,
                'guid': entry.get('id', audio_url),  # Use id or fallback to URL
                'duration_seconds': duration_seconds,
                'link': entry.get('link', ''),
            }

        except Exception as e:
            logger.error(f"Failed to parse episode: {e}")
            return None

    @staticmethod
    def get_new_episodes(
        url: str,
        existing_guids: List[str],
        max_age_days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get new episodes that don't exist in the database.

        Args:
            url: RSS feed URL
            existing_guids: List of GUIDs already in database
            max_age_days: Only get episodes newer than this many days

        Returns:
            List of new episodes
        """
        feed_data = FeedParser.parse_feed(url)
        if not feed_data:
            return []

        new_episodes = []
        cutoff_date = None

        if max_age_days:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=max_age_days)

        for episode in feed_data['episodes']:
            # Check if episode already exists
            if episode['guid'] in existing_guids:
                continue

            # Check age if specified
            if cutoff_date and episode['published_date']:
                if episode['published_date'] < cutoff_date:
                    continue

            new_episodes.append(episode)

        logger.info(f"Found {len(new_episodes)} new episodes")
        return new_episodes
