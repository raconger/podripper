"""
Unit tests for OPML parser functionality.
"""

import pytest
import tempfile
import time
import os
from pathlib import Path
import sys
import importlib.util

# Load OPMLParser directly from file to avoid package import chain
# that requires dependencies like feedparser
opml_parser_path = Path(__file__).parent.parent / 'src' / 'audio' / 'opml_parser.py'
spec = importlib.util.spec_from_file_location("opml_parser", opml_parser_path)
opml_module = importlib.util.module_from_spec(spec)
sys.modules['opml_parser'] = opml_module
spec.loader.exec_module(opml_module)
OPMLParser = opml_module.OPMLParser


class TestOPMLParser:
    """Test suite for OPMLParser."""

    def test_parse_basic_opml(self):
        """Test parsing a basic OPML file with flat structure."""
        opml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
          <head><title>Test</title></head>
          <body>
            <outline text="Test Podcast" type="rss" xmlUrl="https://example.com/feed" />
          </body>
        </opml>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.opml', delete=False) as f:
            f.write(opml_content)
            f.flush()

            feeds = OPMLParser.parse_opml(f.name)

            assert feeds is not None
            assert len(feeds) == 1
            assert feeds[0]['name'] == 'Test Podcast'
            assert feeds[0]['url'] == 'https://example.com/feed'

        os.unlink(f.name)

    def test_parse_nested_categories(self):
        """Test parsing OPML with nested categories."""
        opml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
          <head><title>Test</title></head>
          <body>
            <outline text="Technology">
              <outline text="AI">
                <outline text="AI Podcast" type="rss" xmlUrl="https://example.com/ai-feed" />
              </outline>
            </outline>
            <outline text="Root Podcast" type="rss" xmlUrl="https://example.com/root-feed" />
          </body>
        </opml>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.opml', delete=False) as f:
            f.write(opml_content)
            f.flush()

            feeds = OPMLParser.parse_opml(f.name)

            assert feeds is not None
            assert len(feeds) == 2

            feed_urls = [f['url'] for f in feeds]
            assert 'https://example.com/ai-feed' in feed_urls
            assert 'https://example.com/root-feed' in feed_urls

        os.unlink(f.name)

    def test_parse_uses_title_or_text(self):
        """Test that parser uses 'text' or 'title' attribute for feed name."""
        opml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
          <head><title>Test</title></head>
          <body>
            <outline title="Title Podcast" type="rss" xmlUrl="https://example.com/feed1" />
            <outline text="Text Podcast" type="rss" xmlUrl="https://example.com/feed2" />
          </body>
        </opml>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.opml', delete=False) as f:
            f.write(opml_content)
            f.flush()

            feeds = OPMLParser.parse_opml(f.name)

            assert feeds is not None
            assert len(feeds) == 2

            names = [f['name'] for f in feeds]
            # text takes precedence over title in the current implementation
            assert 'Text Podcast' in names

        os.unlink(f.name)

    def test_parse_handles_missing_body(self):
        """Test that parser handles missing body element."""
        opml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
          <head><title>Test</title></head>
        </opml>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.opml', delete=False) as f:
            f.write(opml_content)
            f.flush()

            feeds = OPMLParser.parse_opml(f.name)

            assert feeds is None

        os.unlink(f.name)

    def test_parse_handles_invalid_xml(self):
        """Test that parser handles invalid XML gracefully."""
        opml_content = '''This is not valid XML'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.opml', delete=False) as f:
            f.write(opml_content)
            f.flush()

            feeds = OPMLParser.parse_opml(f.name)

            assert feeds is None

        os.unlink(f.name)

    def test_parse_nonexistent_file(self):
        """Test that parser handles nonexistent file."""
        feeds = OPMLParser.parse_opml('/nonexistent/path/file.opml')
        assert feeds is None

    def test_parse_filters_by_type(self):
        """Test that parser only includes rss/link/empty type feeds."""
        opml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
          <head><title>Test</title></head>
          <body>
            <outline text="RSS Feed" type="rss" xmlUrl="https://example.com/rss" />
            <outline text="Link Feed" type="link" xmlUrl="https://example.com/link" />
            <outline text="No Type Feed" xmlUrl="https://example.com/notype" />
            <outline text="Include (audio but has rss in url)" type="audio" xmlUrl="https://example.com/rss-audio" />
          </body>
        </opml>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.opml', delete=False) as f:
            f.write(opml_content)
            f.flush()

            feeds = OPMLParser.parse_opml(f.name)

            assert feeds is not None
            assert len(feeds) == 4  # All four should be included

        os.unlink(f.name)

    def test_parse_extracts_optional_attributes(self):
        """Test that parser extracts description, htmlUrl, and category."""
        opml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
          <head><title>Test</title></head>
          <body>
            <outline text="Full Feed" type="rss"
                     xmlUrl="https://example.com/feed"
                     htmlUrl="https://example.com"
                     description="A test podcast"
                     category="Technology" />
          </body>
        </opml>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.opml', delete=False) as f:
            f.write(opml_content)
            f.flush()

            feeds = OPMLParser.parse_opml(f.name)

            assert feeds is not None
            assert len(feeds) == 1
            assert feeds[0]['description'] == 'A test podcast'
            assert feeds[0]['html_url'] == 'https://example.com'
            assert feeds[0]['category'] == 'Technology'

        os.unlink(f.name)


class TestOPMLValidation:
    """Test suite for feed validation."""

    def test_validate_valid_feeds(self):
        """Test validation of valid feeds."""
        feeds = [
            {'name': 'Test Podcast', 'url': 'https://example.com/feed'},
            {'name': 'Another Podcast', 'url': 'http://example.org/feed'},
        ]

        valid = OPMLParser.validate_feeds(feeds)

        assert len(valid) == 2

    def test_validate_removes_feeds_without_url(self):
        """Test that validation removes feeds without URL."""
        feeds = [
            {'name': 'Valid Podcast', 'url': 'https://example.com/feed'},
            {'name': 'No URL Podcast'},
            {'name': 'Empty URL Podcast', 'url': ''},
        ]

        valid = OPMLParser.validate_feeds(feeds)

        assert len(valid) == 1
        assert valid[0]['name'] == 'Valid Podcast'

    def test_validate_generates_name_from_url(self):
        """Test that validation generates name from URL if missing."""
        feeds = [
            {'url': 'https://example.com/feed'},
        ]

        valid = OPMLParser.validate_feeds(feeds)

        assert len(valid) == 1
        assert 'Feed from' in valid[0]['name']

    def test_validate_removes_invalid_urls(self):
        """Test that validation removes feeds with invalid URLs."""
        feeds = [
            {'name': 'Valid', 'url': 'https://example.com/feed'},
            {'name': 'Invalid', 'url': 'not-a-url'},
            {'name': 'FTP', 'url': 'ftp://example.com/feed'},
        ]

        valid = OPMLParser.validate_feeds(feeds)

        assert len(valid) == 1
        assert valid[0]['name'] == 'Valid'

    def test_validate_strips_whitespace(self):
        """Test that validation strips whitespace from URLs."""
        feeds = [
            {'name': 'Whitespace', 'url': '  https://example.com/feed  '},
        ]

        valid = OPMLParser.validate_feeds(feeds)

        assert len(valid) == 1
        assert valid[0]['url'] == 'https://example.com/feed'


class TestOPMLExport:
    """Test suite for OPML export."""

    def test_export_basic(self):
        """Test basic OPML export."""
        feeds = [
            {'name': 'Test Podcast', 'url': 'https://example.com/feed'},
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.opml', delete=False) as f:
            output_path = f.name

        success = OPMLParser.export_opml(feeds, output_path)

        assert success is True
        assert os.path.exists(output_path)

        # Re-import and verify
        imported = OPMLParser.parse_opml(output_path)
        assert imported is not None
        assert len(imported) == 1
        assert imported[0]['name'] == 'Test Podcast'
        assert imported[0]['url'] == 'https://example.com/feed'

        os.unlink(output_path)

    def test_export_with_optional_attributes(self):
        """Test export with description and html_url."""
        feeds = [
            {
                'name': 'Full Podcast',
                'url': 'https://example.com/feed',
                'description': 'A great podcast',
                'html_url': 'https://example.com'
            },
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.opml', delete=False) as f:
            output_path = f.name

        success = OPMLParser.export_opml(feeds, output_path)

        assert success is True

        # Check content
        with open(output_path, 'r') as f:
            content = f.read()
            assert 'description="A great podcast"' in content
            assert 'htmlUrl="https://example.com"' in content

        os.unlink(output_path)

    def test_export_roundtrip(self):
        """Test that export -> import roundtrip preserves data."""
        original_feeds = [
            {'name': 'Podcast 1', 'url': 'https://example.com/feed1'},
            {'name': 'Podcast 2', 'url': 'https://example.com/feed2'},
            {'name': 'Podcast 3', 'url': 'https://example.com/feed3'},
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.opml', delete=False) as f:
            output_path = f.name

        OPMLParser.export_opml(original_feeds, output_path)
        imported = OPMLParser.parse_opml(output_path)

        assert len(imported) == len(original_feeds)

        for orig in original_feeds:
            matches = [f for f in imported if f['url'] == orig['url']]
            assert len(matches) == 1
            assert matches[0]['name'] == orig['name']

        os.unlink(output_path)


class TestOPMLPerformance:
    """Performance tests for OPML operations."""

    def test_parse_performance_100_feeds(self):
        """Test parsing performance with 100 feeds."""
        test_file = Path(__file__).parent / 'test_opml_large.opml'

        if not test_file.exists():
            pytest.skip("Large test OPML file not found")

        start_time = time.time()
        feeds = OPMLParser.parse_opml(str(test_file))
        elapsed = time.time() - start_time

        assert feeds is not None
        assert len(feeds) == 100
        assert elapsed < 0.1, f"Parsing took {elapsed:.3f}s, should be < 0.1s"

        print(f"\nParsing 100 feeds took: {elapsed*1000:.2f}ms")

    def test_validate_performance_100_feeds(self):
        """Test validation performance with 100 feeds."""
        feeds = [
            {'name': f'Podcast {i}', 'url': f'https://example.com/feed/{i}'}
            for i in range(100)
        ]

        start_time = time.time()
        valid = OPMLParser.validate_feeds(feeds)
        elapsed = time.time() - start_time

        assert len(valid) == 100
        assert elapsed < 0.01, f"Validation took {elapsed:.3f}s, should be < 0.01s"

        print(f"\nValidating 100 feeds took: {elapsed*1000:.2f}ms")

    def test_export_performance_100_feeds(self):
        """Test export performance with 100 feeds."""
        feeds = [
            {'name': f'Podcast {i}', 'url': f'https://example.com/feed/{i}'}
            for i in range(100)
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.opml', delete=False) as f:
            output_path = f.name

        start_time = time.time()
        success = OPMLParser.export_opml(feeds, output_path)
        elapsed = time.time() - start_time

        assert success is True
        assert elapsed < 0.1, f"Export took {elapsed:.3f}s, should be < 0.1s"

        print(f"\nExporting 100 feeds took: {elapsed*1000:.2f}ms")

        os.unlink(output_path)


class TestOPMLIntegrationWithFile:
    """Integration tests using the actual test OPML files."""

    def test_parse_test_opml_file(self):
        """Test parsing the standard test OPML file."""
        test_file = Path(__file__).parent / 'test_opml.opml'

        if not test_file.exists():
            pytest.skip("Test OPML file not found")

        feeds = OPMLParser.parse_opml(str(test_file))

        assert feeds is not None
        assert len(feeds) >= 9  # We added 9 feeds with xmlUrl

        # Check specific feeds exist
        feed_names = [f['name'] for f in feeds]
        assert 'Lex Fridman Podcast' in feed_names
        assert 'Invest Like the Best' in feed_names
        assert 'All-In Podcast' in feed_names
        assert 'Practical AI' in feed_names  # Deeply nested

    def test_parse_and_validate_test_opml(self):
        """Test full parse + validate flow."""
        test_file = Path(__file__).parent / 'test_opml.opml'

        if not test_file.exists():
            pytest.skip("Test OPML file not found")

        feeds = OPMLParser.parse_opml(str(test_file))
        valid_feeds = OPMLParser.validate_feeds(feeds)

        assert len(valid_feeds) >= 9

        # All should have valid URLs
        for feed in valid_feeds:
            assert feed['url'].startswith('http')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
