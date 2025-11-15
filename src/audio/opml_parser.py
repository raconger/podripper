"""
OPML file parser for importing podcast feeds.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger


class OPMLParser:
    """Parse OPML files to extract podcast feed information."""

    @staticmethod
    def parse_opml(file_path: str) -> Optional[List[Dict[str, Any]]]:
        """
        Parse an OPML file and extract podcast feeds.

        Args:
            file_path: Path to OPML file

        Returns:
            List of feed dictionaries with name and URL
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"OPML file not found: {file_path}")
                return None

            logger.info(f"Parsing OPML file: {file_path}")

            # Parse XML
            tree = ET.parse(file_path)
            root = tree.getroot()

            feeds = []

            # OPML structure: <opml><body><outline> elements
            # Podcast feeds are typically in outline elements with xmlUrl attribute
            body = root.find('body')
            if body is None:
                logger.error("Invalid OPML file: no <body> element found")
                return None

            # Recursively find all outline elements (feeds can be nested in categories)
            def extract_feeds(element):
                for outline in element.findall('outline'):
                    # Check if this outline has an xmlUrl (indicates it's a feed)
                    xml_url = outline.get('xmlUrl')

                    if xml_url:
                        # This is a feed
                        feed_name = outline.get('text') or outline.get('title') or 'Unnamed Feed'
                        feed_type = outline.get('type', '')

                        # Only include RSS/podcast feeds
                        if feed_type in ['rss', 'link', ''] or 'rss' in xml_url.lower():
                            feeds.append({
                                'name': feed_name,
                                'url': xml_url,
                                'description': outline.get('description', ''),
                                'html_url': outline.get('htmlUrl', ''),
                                'category': outline.get('category', ''),
                            })
                    else:
                        # This might be a category folder, recurse into it
                        extract_feeds(outline)

            extract_feeds(body)

            logger.info(f"Found {len(feeds)} podcast feeds in OPML file")
            return feeds

        except ET.ParseError as e:
            logger.error(f"Failed to parse OPML file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing OPML file {file_path}: {e}")
            return None

    @staticmethod
    def export_opml(feeds: List[Dict[str, Any]], output_path: str, title: str = "PodRipper Feeds") -> bool:
        """
        Export feeds to an OPML file.

        Args:
            feeds: List of feed dictionaries with 'name' and 'url'
            output_path: Path to save OPML file
            title: Title for the OPML file

        Returns:
            True if successful
        """
        try:
            # Create OPML structure
            opml = ET.Element('opml', version='2.0')

            # Head
            head = ET.SubElement(opml, 'head')
            title_elem = ET.SubElement(head, 'title')
            title_elem.text = title

            # Body
            body = ET.SubElement(opml, 'body')

            # Add feeds
            for feed in feeds:
                outline = ET.SubElement(
                    body,
                    'outline',
                    type='rss',
                    text=feed.get('name', 'Unnamed Feed'),
                    xmlUrl=feed.get('url', ''),
                )

                if feed.get('description'):
                    outline.set('description', feed['description'])
                if feed.get('html_url'):
                    outline.set('htmlUrl', feed['html_url'])

            # Write to file
            tree = ET.ElementTree(opml)
            ET.indent(tree, space='  ')  # Pretty print
            tree.write(output_path, encoding='utf-8', xml_declaration=True)

            logger.info(f"Exported {len(feeds)} feeds to OPML: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export OPML to {output_path}: {e}")
            return False

    @staticmethod
    def validate_feeds(feeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and clean feed data.

        Args:
            feeds: List of feed dictionaries

        Returns:
            List of validated feeds
        """
        valid_feeds = []

        for feed in feeds:
            # Must have URL
            if not feed.get('url'):
                logger.warning(f"Skipping feed without URL: {feed.get('name')}")
                continue

            # Must have name
            if not feed.get('name'):
                feed['name'] = f"Feed from {feed['url']}"

            # Clean URL
            url = feed['url'].strip()
            if not url.startswith('http'):
                logger.warning(f"Skipping invalid URL: {url}")
                continue

            feed['url'] = url
            valid_feeds.append(feed)

        return valid_feeds
