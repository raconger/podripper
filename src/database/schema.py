"""
Database schema definitions for the podcast processing system.
"""

SCHEMA_VERSION = 1

# SQL statements for creating tables
CREATE_TABLES = """
-- Podcast feeds table
CREATE TABLE IF NOT EXISTS feeds (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    url VARCHAR NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT true,
    last_checked TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Episodes table
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY,
    feed_id INTEGER NOT NULL,
    title VARCHAR NOT NULL,
    description TEXT,
    audio_url VARCHAR NOT NULL,
    published_date TIMESTAMP,
    duration_seconds INTEGER,
    guid VARCHAR UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (feed_id) REFERENCES feeds(id)
);

-- Processing status table
CREATE TABLE IF NOT EXISTS processing_status (
    episode_id INTEGER PRIMARY KEY,
    status VARCHAR NOT NULL, -- pending, downloading, transcribing, cleaning, summarizing, completed, failed
    audio_path VARCHAR,
    raw_transcript_path VARCHAR,
    cleaned_transcript_path VARCHAR,
    summary_path VARCHAR,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (episode_id) REFERENCES episodes(id)
);

-- Transcripts table (stores actual content)
CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY,
    episode_id INTEGER NOT NULL,
    raw_text TEXT,
    cleaned_text TEXT,
    transcription_model VARCHAR,
    cleaning_model VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (episode_id) REFERENCES episodes(id)
);

-- Summaries table
CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY,
    episode_id INTEGER NOT NULL,
    host_and_guest TEXT,
    comprehensive_summary TEXT,
    key_topics TEXT, -- JSON array
    actionable_quotes TEXT, -- JSON array
    investment_theses TEXT, -- JSON array
    noteworthy_observations TEXT, -- JSON array
    company_mentions TEXT, -- JSON array
    model_used VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (episode_id) REFERENCES episodes(id)
);

-- Processing logs
CREATE TABLE IF NOT EXISTS processing_logs (
    id INTEGER PRIMARY KEY,
    episode_id INTEGER,
    stage VARCHAR NOT NULL, -- download, transcribe, clean, summarize
    status VARCHAR NOT NULL, -- success, error, warning
    message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (episode_id) REFERENCES episodes(id)
);

-- Metadata table for schema version tracking
CREATE TABLE IF NOT EXISTS metadata (
    key VARCHAR PRIMARY KEY,
    value VARCHAR NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert schema version
INSERT OR REPLACE INTO metadata (key, value) VALUES ('schema_version', '1');
"""

# Indexes for better query performance
CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_episodes_feed_id ON episodes(feed_id);
CREATE INDEX IF NOT EXISTS idx_episodes_published_date ON episodes(published_date);
CREATE INDEX IF NOT EXISTS idx_episodes_guid ON episodes(guid);
CREATE INDEX IF NOT EXISTS idx_processing_status_status ON processing_status(status);
CREATE INDEX IF NOT EXISTS idx_processing_logs_episode_id ON processing_logs(episode_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_timestamp ON processing_logs(timestamp);
"""
