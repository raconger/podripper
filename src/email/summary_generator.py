"""
Weekly summary email generator.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger


class WeeklySummaryGenerator:
    """Generate HTML email summaries of processed podcasts."""

    def __init__(self, db_manager):
        """
        Initialize summary generator.

        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager

    def get_weekly_episodes(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get episodes completed in the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of episode dictionaries
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        with self.db.get_connection() as conn:
            results = conn.execute(
                """
                SELECT
                    e.id,
                    e.title,
                    e.published_date,
                    f.name as feed_name,
                    ps.completed_at,
                    ps.summary_path
                FROM episodes e
                JOIN feeds f ON e.feed_id = f.id
                JOIN processing_status ps ON e.id = ps.episode_id
                WHERE ps.status = 'completed'
                  AND ps.completed_at >= ?
                ORDER BY ps.completed_at DESC
                """,
                [cutoff_date]
            ).fetchall()

            episodes = []
            for r in results:
                episodes.append({
                    'id': r[0],
                    'title': r[1],
                    'published_date': r[2],
                    'feed_name': r[3],
                    'completed_at': r[4],
                    'summary_path': r[5]
                })

            return episodes

    def get_episode_summary(self, episode_id: int) -> Optional[Dict[str, Any]]:
        """
        Get summary data for an episode.

        Args:
            episode_id: Episode ID

        Returns:
            Summary dictionary
        """
        with self.db.get_connection() as conn:
            result = conn.execute(
                """
                SELECT
                    host_and_guest,
                    comprehensive_summary,
                    key_topics,
                    actionable_quotes,
                    investment_theses,
                    noteworthy_observations,
                    company_mentions
                FROM summaries
                WHERE episode_id = ?
                """,
                [episode_id]
            ).fetchone()

            if not result:
                return None

            # Parse JSON fields
            return {
                'host_and_guest': result[0],
                'comprehensive_summary': result[1],
                'key_topics': json.loads(result[2]) if result[2] else [],
                'actionable_quotes': json.loads(result[3]) if result[3] else [],
                'investment_theses': json.loads(result[4]) if result[4] else [],
                'noteworthy_observations': json.loads(result[5]) if result[5] else [],
                'company_mentions': json.loads(result[6]) if result[6] else []
            }

    def generate_html_email(
        self,
        episodes: List[Dict[str, Any]],
        include_full_summaries: bool = False
    ) -> str:
        """
        Generate HTML email content.

        Args:
            episodes: List of episode dictionaries
            include_full_summaries: Whether to include full summaries or just highlights

        Returns:
            HTML email content
        """
        if not episodes:
            return self._generate_no_episodes_html()

        # Start HTML
        html_parts = [self._get_html_header()]

        # Title and intro
        date_range = self._get_date_range(episodes)
        html_parts.append(f"""
        <div class="header">
            <h1>🎧 Your Weekly Podcast Digest</h1>
            <p class="subtitle">{date_range}</p>
            <p class="summary-count">{len(episodes)} episode{'' if len(episodes) == 1 else 's'} processed this week</p>
        </div>
        """)

        # Table of contents
        html_parts.append('<div class="toc">')
        html_parts.append('<h2>This Week\'s Episodes</h2>')
        html_parts.append('<ul>')
        for i, ep in enumerate(episodes):
            html_parts.append(
                f'<li><a href="#episode-{i}">{ep["title"]}</a> <span class="feed">({ep["feed_name"]})</span></li>'
            )
        html_parts.append('</ul>')
        html_parts.append('</div>')

        # Episode summaries
        for i, episode in enumerate(episodes):
            summary = self.get_episode_summary(episode['id'])
            if summary:
                html_parts.append(
                    self._generate_episode_html(episode, summary, i, include_full_summaries)
                )

        # Footer
        html_parts.append(self._get_html_footer())

        return '\n'.join(html_parts)

    def _generate_episode_html(
        self,
        episode: Dict[str, Any],
        summary: Dict[str, Any],
        index: int,
        include_full: bool
    ) -> str:
        """Generate HTML for a single episode."""
        html = f"""
        <div class="episode" id="episode-{index}">
            <h2 class="episode-title">{episode['title']}</h2>
            <p class="episode-meta">
                <strong>{episode['feed_name']}</strong> •
                {self._format_date(episode['published_date'])}
            </p>
        """

        # Host and Guest
        if summary.get('host_and_guest'):
            html += f"""
            <div class="section">
                <h3>🎙️ Host and Guest</h3>
                <p>{summary['host_and_guest']}</p>
            </div>
            """

        # Comprehensive Summary
        if summary.get('comprehensive_summary'):
            html += f"""
            <div class="section">
                <h3>📝 Summary</h3>
                <p>{summary['comprehensive_summary']}</p>
            </div>
            """

        # Top Quotes (limit to 3 for email)
        quotes = summary.get('actionable_quotes', [])[:3]
        if quotes:
            html += '<div class="section"><h3>💬 Top Quotes</h3>'
            for quote in quotes:
                html += f"""
                <blockquote>
                    "{quote.get('quote', '')}"
                    <footer>— {quote.get('speaker', 'Unknown')}</footer>
                </blockquote>
                """
            html += '</div>'

        # Investment Theses (if any)
        theses = summary.get('investment_theses', [])
        if theses and include_full:
            html += '<div class="section"><h3>💡 Investment Theses</h3><ul>'
            for thesis in theses:
                html += f"<li><strong>{thesis.get('thesis', '')}</strong>: {thesis.get('reasoning', '')}</li>"
            html += '</ul></div>'

        # Key Topics (show first 5)
        topics = summary.get('key_topics', [])[:5]
        if topics:
            html += '<div class="section"><h3>🔑 Key Topics</h3><ul>'
            for topic in topics:
                html += f"<li><strong>{topic.get('topic', '')}</strong>: {topic.get('description', '')}</li>"
            html += '</ul></div>'

        # Company Mentions
        companies = summary.get('company_mentions', [])[:5]
        if companies:
            html += '<div class="section"><h3>🏢 Companies Mentioned</h3><ul>'
            for company in companies:
                html += f"<li><strong>{company.get('name', '')}</strong> ({company.get('industry', 'N/A')}): {company.get('context', '')}</li>"
            html += '</ul></div>'

        html += '</div><hr>'
        return html

    def _generate_no_episodes_html(self) -> str:
        """Generate HTML for when no episodes were processed."""
        html = self._get_html_header()
        html += """
        <div class="header">
            <h1>🎧 Your Weekly Podcast Digest</h1>
            <p class="subtitle">No episodes processed this week</p>
        </div>
        <div class="episode">
            <p>No podcast episodes were processed in the last 7 days. Check your feeds or processing status.</p>
        </div>
        """
        html += self._get_html_footer()
        return html

    def _get_html_header(self) -> str:
        """Get HTML header with styles."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                    text-align: center;
                }
                .header h1 {
                    margin: 0;
                    font-size: 2em;
                }
                .subtitle {
                    opacity: 0.9;
                    margin: 10px 0;
                }
                .summary-count {
                    font-size: 1.2em;
                    font-weight: bold;
                    margin-top: 10px;
                }
                .toc {
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .toc h2 {
                    margin-top: 0;
                    color: #667eea;
                }
                .toc ul {
                    list-style: none;
                    padding: 0;
                }
                .toc li {
                    padding: 8px 0;
                    border-bottom: 1px solid #eee;
                }
                .toc li:last-child {
                    border-bottom: none;
                }
                .toc a {
                    color: #333;
                    text-decoration: none;
                    font-weight: 500;
                }
                .toc a:hover {
                    color: #667eea;
                }
                .feed {
                    color: #666;
                    font-size: 0.9em;
                }
                .episode {
                    background: white;
                    padding: 25px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .episode-title {
                    color: #667eea;
                    margin-top: 0;
                }
                .episode-meta {
                    color: #666;
                    font-size: 0.9em;
                    margin-bottom: 20px;
                }
                .section {
                    margin: 20px 0;
                }
                .section h3 {
                    color: #764ba2;
                    margin-bottom: 10px;
                }
                blockquote {
                    border-left: 4px solid #667eea;
                    margin: 15px 0;
                    padding: 10px 20px;
                    background: #f8f9fa;
                    font-style: italic;
                }
                blockquote footer {
                    margin-top: 10px;
                    font-style: normal;
                    color: #666;
                    font-weight: bold;
                }
                ul {
                    padding-left: 20px;
                }
                li {
                    margin-bottom: 10px;
                }
                hr {
                    border: none;
                    border-top: 1px solid #eee;
                    margin: 30px 0;
                }
                .footer {
                    text-align: center;
                    padding: 20px;
                    color: #666;
                    font-size: 0.9em;
                }
            </style>
        </head>
        <body>
        """

    def _get_html_footer(self) -> str:
        """Get HTML footer."""
        return """
        <div class="footer">
            <p>Generated by PodRipper 🎧</p>
            <p style="font-size: 0.8em; color: #999;">
                This is an automated weekly digest. Summaries generated using AI.
            </p>
        </div>
        </body>
        </html>
        """

    def _get_date_range(self, episodes: List[Dict[str, Any]]) -> str:
        """Get formatted date range for episodes."""
        if not episodes:
            return ""

        dates = [ep['completed_at'] for ep in episodes if ep.get('completed_at')]
        if not dates:
            return "This Week"

        oldest = min(dates)
        newest = max(dates)

        if isinstance(oldest, str):
            oldest = datetime.fromisoformat(oldest.replace('Z', '+00:00'))
        if isinstance(newest, str):
            newest = datetime.fromisoformat(newest.replace('Z', '+00:00'))

        if oldest.date() == newest.date():
            return oldest.strftime("%B %d, %Y")
        else:
            return f"{oldest.strftime('%B %d')} - {newest.strftime('%B %d, %Y')}"

    def _format_date(self, date) -> str:
        """Format date for display."""
        if not date:
            return "Unknown date"

        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except:
                return date

        return date.strftime("%B %d, %Y")

    def generate_text_email(self, episodes: List[Dict[str, Any]]) -> str:
        """
        Generate plain text email content.

        Args:
            episodes: List of episode dictionaries

        Returns:
            Plain text email content
        """
        if not episodes:
            return "No podcast episodes were processed this week."

        lines = ["YOUR WEEKLY PODCAST DIGEST", "=" * 50, ""]
        lines.append(f"{len(episodes)} episode{'s' if len(episodes) > 1 else ''} processed this week\n")

        for i, episode in enumerate(episodes, 1):
            summary = self.get_episode_summary(episode['id'])
            if not summary:
                continue

            lines.append(f"\n{i}. {episode['title']}")
            lines.append(f"   {episode['feed_name']}")
            lines.append("-" * 50)

            if summary.get('comprehensive_summary'):
                lines.append(f"\n{summary['comprehensive_summary']}\n")

            # Top quotes
            quotes = summary.get('actionable_quotes', [])[:2]
            if quotes:
                lines.append("Top Quotes:")
                for quote in quotes:
                    lines.append(f'  "{quote.get("quote", "")}" - {quote.get("speaker", "Unknown")}')
                lines.append("")

        lines.append("\n" + "=" * 50)
        lines.append("Generated by PodRipper")

        return '\n'.join(lines)
