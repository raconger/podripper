"""
Performance tests for OPML import flow including database operations.
This tests the complete import-opml command flow and identifies bottlenecks.
"""

import time
import tempfile
import os
from pathlib import Path
import sys
import importlib.util
import duckdb

# Load OPMLParser directly to avoid dependency chain issues
opml_parser_path = Path(__file__).parent.parent / 'src' / 'audio' / 'opml_parser.py'
spec = importlib.util.spec_from_file_location("opml_parser", opml_parser_path)
opml_module = importlib.util.module_from_spec(spec)
sys.modules['opml_parser'] = opml_module
spec.loader.exec_module(opml_module)
OPMLParser = opml_module.OPMLParser


# Database schema (inline to avoid import issues)
CREATE_TABLES = """
CREATE SEQUENCE IF NOT EXISTS feeds_id_seq;
CREATE TABLE IF NOT EXISTS feeds (
    id INTEGER DEFAULT nextval('feeds_id_seq') PRIMARY KEY,
    name VARCHAR NOT NULL,
    url VARCHAR NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT true,
    last_checked TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db(db_path: str):
    """Initialize database with schema."""
    conn = duckdb.connect(db_path)
    conn.execute(CREATE_TABLES)
    conn.close()


def add_feed_single_connection(conn, name: str, url: str, enabled: bool = True):
    """Add feed using existing connection."""
    result = conn.execute(
        """
        INSERT INTO feeds (name, url, enabled)
        VALUES (?, ?, ?)
        ON CONFLICT (url) DO UPDATE SET
            name = excluded.name,
            enabled = excluded.enabled
        RETURNING id
        """,
        [name, url, enabled]
    ).fetchone()
    return result[0] if result else None


def add_feed_new_connection(db_path: str, name: str, url: str, enabled: bool = True):
    """Add feed with new connection (simulates current implementation)."""
    conn = duckdb.connect(db_path)
    try:
        result = conn.execute(
            """
            INSERT INTO feeds (name, url, enabled)
            VALUES (?, ?, ?)
            ON CONFLICT (url) DO UPDATE SET
                name = excluded.name,
                enabled = excluded.enabled
            RETURNING id
            """,
            [name, url, enabled]
        ).fetchone()
        return result[0] if result else None
    finally:
        conn.close()


def generate_test_feeds(count: int):
    """Generate test feed data."""
    return [
        {'name': f'Podcast {i}', 'url': f'https://example.com/feed/{i}'}
        for i in range(count)
    ]


def generate_opml_file(count: int, output_path: str):
    """Generate an OPML file with specified number of feeds."""
    feeds = generate_test_feeds(count)
    OPMLParser.export_opml(feeds, output_path)
    return output_path


class TestCurrentImportPerformance:
    """Test and measure current import performance."""

    def test_current_import_100_feeds(self):
        """Measure time to import 100 feeds with current implementation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test OPML
            opml_path = os.path.join(tmpdir, 'test.opml')
            generate_opml_file(100, opml_path)

            # Create test database
            db_path = os.path.join(tmpdir, 'test.duckdb')
            init_db(db_path)

            # Parse OPML
            start = time.time()
            feeds = OPMLParser.parse_opml(opml_path)
            parse_time = time.time() - start

            # Validate feeds
            start = time.time()
            valid_feeds = OPMLParser.validate_feeds(feeds)
            validate_time = time.time() - start

            # Import to database (current slow method - new connection per insert)
            start = time.time()
            for feed in valid_feeds:
                add_feed_new_connection(db_path, feed['name'], feed['url'], True)
            db_time = time.time() - start

            total_time = parse_time + validate_time + db_time

            print(f"\n=== Current Implementation (100 feeds) ===")
            print(f"  OPML Parse:     {parse_time*1000:.2f}ms")
            print(f"  Validation:     {validate_time*1000:.2f}ms")
            print(f"  DB Insert:      {db_time*1000:.2f}ms")
            print(f"  ---")
            print(f"  TOTAL:          {total_time*1000:.2f}ms")
            print(f"  Per feed:       {total_time/100*1000:.2f}ms")

            # Verify import
            conn = duckdb.connect(db_path)
            count = conn.execute("SELECT COUNT(*) FROM feeds").fetchone()[0]
            conn.close()
            assert count == 100

    def test_current_import_500_feeds(self):
        """Measure time to import 500 feeds (stress test)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test OPML
            opml_path = os.path.join(tmpdir, 'test.opml')
            generate_opml_file(500, opml_path)

            # Create test database
            db_path = os.path.join(tmpdir, 'test.duckdb')
            init_db(db_path)

            # Full import flow with current method
            start = time.time()
            feeds = OPMLParser.parse_opml(opml_path)
            valid_feeds = OPMLParser.validate_feeds(feeds)

            for feed in valid_feeds:
                add_feed_new_connection(db_path, feed['name'], feed['url'], True)
            total_time = time.time() - start

            print(f"\n=== Current Implementation (500 feeds) ===")
            print(f"  TOTAL:          {total_time*1000:.2f}ms")
            print(f"  Per feed:       {total_time/500*1000:.2f}ms")

            # Verify import
            conn = duckdb.connect(db_path)
            count = conn.execute("SELECT COUNT(*) FROM feeds").fetchone()[0]
            conn.close()
            assert count == 500


class TestOptimizedImportPerformance:
    """Test optimized import implementation for performance comparison."""

    def test_optimized_import_100_feeds(self):
        """Test single-connection batch import for 100 feeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test OPML
            opml_path = os.path.join(tmpdir, 'test.opml')
            generate_opml_file(100, opml_path)

            # Create test database
            db_path = os.path.join(tmpdir, 'test.duckdb')
            init_db(db_path)

            # Parse OPML
            start = time.time()
            feeds = OPMLParser.parse_opml(opml_path)
            parse_time = time.time() - start

            # Validate feeds
            start = time.time()
            valid_feeds = OPMLParser.validate_feeds(feeds)
            validate_time = time.time() - start

            # Optimized: Single connection for all inserts
            start = time.time()
            conn = duckdb.connect(db_path)
            try:
                for feed in valid_feeds:
                    add_feed_single_connection(conn, feed['name'], feed['url'], True)
            finally:
                conn.close()
            db_time = time.time() - start

            total_time = parse_time + validate_time + db_time

            print(f"\n=== Optimized (Single Connection) - 100 feeds ===")
            print(f"  OPML Parse:     {parse_time*1000:.2f}ms")
            print(f"  Validation:     {validate_time*1000:.2f}ms")
            print(f"  DB Insert:      {db_time*1000:.2f}ms")
            print(f"  ---")
            print(f"  TOTAL:          {total_time*1000:.2f}ms")
            print(f"  Per feed:       {total_time/100*1000:.2f}ms")

    def test_optimized_import_500_feeds(self):
        """Test single-connection batch import for 500 feeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test OPML
            opml_path = os.path.join(tmpdir, 'test.opml')
            generate_opml_file(500, opml_path)

            # Create test database
            db_path = os.path.join(tmpdir, 'test.duckdb')
            init_db(db_path)

            # Optimized full import flow
            start = time.time()
            feeds = OPMLParser.parse_opml(opml_path)
            valid_feeds = OPMLParser.validate_feeds(feeds)

            conn = duckdb.connect(db_path)
            try:
                for feed in valid_feeds:
                    add_feed_single_connection(conn, feed['name'], feed['url'], True)
            finally:
                conn.close()
            total_time = time.time() - start

            print(f"\n=== Optimized (Single Connection) - 500 feeds ===")
            print(f"  TOTAL:          {total_time*1000:.2f}ms")
            print(f"  Per feed:       {total_time/500*1000:.2f}ms")

            # Verify import
            conn = duckdb.connect(db_path)
            count = conn.execute("SELECT COUNT(*) FROM feeds").fetchone()[0]
            conn.close()
            assert count == 500


class TestConnectionOverhead:
    """Test the impact of connection overhead."""

    def test_connection_overhead_comparison(self):
        """Compare multi-connection vs single-connection performance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.duckdb')
            init_db(db_path)

            feeds = generate_test_feeds(100)

            # Method 1: New connection per insert (current approach)
            start = time.time()
            for feed in feeds:
                add_feed_new_connection(
                    db_path,
                    feed['name'] + '_m1',
                    feed['url'] + '_m1',
                    True
                )
            multi_conn_time = time.time() - start

            # Method 2: Single connection for all inserts
            start = time.time()
            conn = duckdb.connect(db_path)
            try:
                for feed in feeds:
                    add_feed_single_connection(
                        conn,
                        feed['name'] + '_m2',
                        feed['url'] + '_m2',
                        True
                    )
            finally:
                conn.close()
            single_conn_time = time.time() - start

            speedup = multi_conn_time / single_conn_time if single_conn_time > 0 else float('inf')

            print(f"\n=== Connection Overhead Analysis (100 inserts) ===")
            print(f"  Multi-connection:  {multi_conn_time*1000:.2f}ms ({multi_conn_time/100*1000:.3f}ms/insert)")
            print(f"  Single-connection: {single_conn_time*1000:.2f}ms ({single_conn_time/100*1000:.3f}ms/insert)")
            print(f"  ---")
            print(f"  Speedup:           {speedup:.1f}x faster")
            print(f"  Time saved:        {(multi_conn_time - single_conn_time)*1000:.2f}ms")


class TestDuplicateHandling:
    """Test performance of handling duplicate imports."""

    def test_reimport_same_feeds(self):
        """Test performance when re-importing the same feeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.duckdb')
            init_db(db_path)

            feeds = generate_test_feeds(100)

            # First import
            conn = duckdb.connect(db_path)
            start = time.time()
            for feed in feeds:
                add_feed_single_connection(conn, feed['name'], feed['url'], True)
            first_import_time = time.time() - start

            # Second import (all duplicates with ON CONFLICT)
            start = time.time()
            for feed in feeds:
                add_feed_single_connection(conn, feed['name'], feed['url'], True)
            second_import_time = time.time() - start
            conn.close()

            print(f"\n=== Duplicate Import Performance (100 feeds) ===")
            print(f"  First import:   {first_import_time*1000:.2f}ms")
            print(f"  Second import:  {second_import_time*1000:.2f}ms (all duplicates)")
            print(f"  Ratio:          {second_import_time/first_import_time:.2f}x")


class TestScalability:
    """Test scalability with varying feed counts."""

    def test_scalability_comparison(self):
        """Compare performance at different scales."""
        results = []

        for count in [10, 50, 100, 200, 500]:
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = os.path.join(tmpdir, 'test.duckdb')
                init_db(db_path)

                feeds = generate_test_feeds(count)

                # Single connection method
                conn = duckdb.connect(db_path)
                start = time.time()
                for feed in feeds:
                    add_feed_single_connection(conn, feed['name'], feed['url'], True)
                elapsed = time.time() - start
                conn.close()

                results.append({
                    'count': count,
                    'time_ms': elapsed * 1000,
                    'per_feed_ms': elapsed / count * 1000
                })

        print(f"\n=== Scalability Analysis (Single Connection) ===")
        print(f"  {'Feeds':>6} | {'Total (ms)':>12} | {'Per Feed (ms)':>14}")
        print(f"  {'-'*6} | {'-'*12} | {'-'*14}")
        for r in results:
            print(f"  {r['count']:>6} | {r['time_ms']:>12.2f} | {r['per_feed_ms']:>14.3f}")


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v', '-s'])
