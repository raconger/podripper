# PodRipper - Podcast Processing & Summarization System

A comprehensive Python-based system for downloading, transcribing, cleaning, and summarizing podcast episodes with structured analysis.

## Features

- **Automated Audio Processing**: Download podcast episodes from RSS feeds using yt-dlp
- **OPML Import/Export**: Import your podcast subscriptions from any podcast app
- **High-Quality Transcription**: Support for both local Whisper models and OpenAI's API
- **AI-Powered Cleaning**: Use Claude, GPT-4, or local Ollama models to clean transcripts
- **Structured Summarization**: Generate comprehensive summaries with:
  - Host and guest identification
  - Comprehensive overview
  - Key topics and themes
  - Actionable quotes with context
  - Investment theses and market insights
  - Noteworthy observations
  - Company mentions with details
- **Weekly Email Digest**: Beautiful HTML emails with summaries sent to your inbox every Saturday
- **Robust Database**: DuckDB-based storage for metadata, transcripts, and summaries
- **Batch Processing**: Orchestrated pipeline for processing multiple episodes
- **Flexible Configuration**: YAML-based config with environment variable support

## Requirements

- Python 3.10+
- ffmpeg (for audio processing)
- CUDA-capable GPU (optional, for faster local transcription)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd podripper
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install ffmpeg

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### 5. Initialize Configuration

```bash
python podripper.py init
```

This creates `config.yaml` and `.env` from templates.

### 6. Configure API Keys

Edit `.env` and add your API keys:

```bash
# For Claude (recommended for best quality)
ANTHROPIC_API_KEY=your_key_here

# Or for OpenAI
OPENAI_API_KEY=your_key_here

# Choose your provider
LLM_PROVIDER=anthropic  # or openai, or ollama

# For transcription
TRANSCRIPTION_PROVIDER=whisper  # or openai
WHISPER_MODEL=base  # tiny, base, small, medium, large
```

### 7. Configure Podcast Feeds

**Option A: Import from OPML** (recommended if you already use a podcast app)

Export your subscriptions from your podcast app (Apple Podcasts, Overcast, Pocket Casts, etc.) and import:

```bash
python podripper.py import-opml podcasts.opml
```

See [OPML Import Guide](docs/OPML_IMPORT.md) for detailed instructions.

**Option B: Manual Configuration**

Edit `config.yaml` and add your podcast feeds:

```yaml
feeds:
  - name: "Lex Fridman Podcast"
    url: "https://lexfridman.com/feed/podcast/"
    enabled: true
  - name: "Your Favorite Podcast"
    url: "https://example.com/feed.xml"
    enabled: true
```

### 8. (Optional) Configure Weekly Email

To receive a weekly digest email every Saturday morning, see the [Email Setup Guide](docs/EMAIL_SETUP.md).

## Usage

### Quick Start

Run the complete workflow (sync feeds and process episodes):

```bash
python podripper.py run
```

### Step-by-Step Workflow

#### 1. Sync Podcast Feeds

Download feed metadata and add new episodes to the database:

```bash
python podripper.py sync
```

#### 2. Process Episodes

Process pending episodes through the complete pipeline:

```bash
# Process all pending episodes (respects max_episodes_per_run in config)
python podripper.py process

# Process specific number of episodes
python podripper.py process --limit 3

# Process specific episode by ID
python podripper.py process --episode-id 42
```

### Management Commands

#### Feed Management

```bash
# List all feeds
python podripper.py list-feeds

# Add a feed manually
python podripper.py add-feed "Podcast Name" "https://feed-url.com/rss"

# Import feeds from OPML (from podcast apps)
python podripper.py import-opml podcasts.opml

# Export feeds to OPML
python podripper.py export-opml --output my-feeds.opml
```

#### Episode Management

```bash
# List all episodes
python podripper.py list-episodes

# List by status
python podripper.py list-episodes --status pending
python podripper.py list-episodes --status completed
python podripper.py list-episodes --status failed

# Limit results
python podripper.py list-episodes --limit 20
```

#### Statistics & Email

```bash
# View processing statistics
python podripper.py stats

# Send weekly digest email
python podripper.py send-email

# Test email configuration
python podripper.py test-email
```

## Configuration

### Environment Variables (.env)

```bash
# API Keys
ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=sk-...

# LLM Provider (anthropic, openai, ollama)
LLM_PROVIDER=anthropic

# Ollama Configuration (if using local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# Transcription Provider (whisper, openai)
TRANSCRIPTION_PROVIDER=whisper
WHISPER_MODEL=base

# Paths
DATABASE_PATH=data/podcasts.duckdb
AUDIO_DIR=data/audio
TRANSCRIPTS_DIR=data/transcripts
SUMMARIES_DIR=data/summaries

# Logging
LOG_LEVEL=INFO
LOG_FILE=data/podripper.log
```

### YAML Configuration (config.yaml)

```yaml
feeds:
  - name: "Podcast Name"
    url: "https://feed-url.com/rss"
    enabled: true

processing:
  max_episodes_per_run: 5
  newest_first: true
  max_age_days: 30  # Only process episodes from last 30 days (0 = no limit)
  concurrent_workers: 1

audio:
  format: "mp3"
  quality: "good"  # best, good, medium
  delete_after_transcription: false

transcription:
  language: null  # Auto-detect
  word_timestamps: false
  temperature: 0.0

cleaning:
  model: "claude-3-5-sonnet-20241022"
  temperature: 0.3
  max_tokens: 4000

summarization:
  model: "claude-3-5-sonnet-20241022"
  temperature: 0.5
  max_tokens: 4000
  output_format: "both"  # json, markdown, both
```

## Output Structure

After processing, files are organized as follows:

```
data/
├── podcasts.duckdb          # Database file
├── audio/                   # Downloaded audio files
│   └── 1_episode_title_hash.mp3
├── transcripts/             # Transcript files
│   ├── 1_raw.txt           # Raw transcription
│   └── 1_cleaned.txt       # Cleaned transcript
└── summaries/              # Summary files
    ├── 1_summary.json      # Structured summary (JSON)
    └── 1_summary.md        # Formatted summary (Markdown)
```

## Summary Output Format

### JSON Structure

```json
{
  "host_and_guest": "Host: John Doe, Technology Journalist. Guest: Jane Smith, CEO of TechCorp...",
  "comprehensive_summary": "In this episode...",
  "key_topics": [
    {
      "topic": "Artificial Intelligence",
      "description": "Discussion about the current state..."
    }
  ],
  "actionable_quotes": [
    {
      "quote": "The future of AI is...",
      "speaker": "Jane Smith",
      "context": "When discussing AI safety..."
    }
  ],
  "investment_theses": [
    {
      "thesis": "Enterprise AI adoption will accelerate",
      "reasoning": "Due to improved tooling...",
      "risks": "Regulatory uncertainty..."
    }
  ],
  "noteworthy_observations": [
    "Observation 1...",
    "Observation 2..."
  ],
  "company_mentions": [
    {
      "name": "OpenAI",
      "industry": "Artificial Intelligence",
      "context": "Discussed their latest model release",
      "details": "Reached 100M users in 2 months"
    }
  ]
}
```

### Markdown Format

The markdown output provides a formatted version with sections:

- Host and Guest
- Comprehensive Summary
- Key Topics and Themes
- Actionable Quotes
- Investment Theses
- Noteworthy Observations
- Company Mentions

## Processing Pipeline

The system processes each episode through four stages:

1. **Download**: Fetch audio from RSS feed URL using yt-dlp
2. **Transcribe**: Convert audio to text using Whisper or OpenAI API
3. **Clean**: Remove filler words and improve readability using LLM
4. **Summarize**: Generate structured summary with key insights

Each stage is logged and tracked in the database.

## Advanced Usage

### Using Local Whisper Models

For privacy or cost savings, use local Whisper:

```bash
TRANSCRIPTION_PROVIDER=whisper
WHISPER_MODEL=base  # Options: tiny, base, small, medium, large
```

Model sizes and performance:
- `tiny`: ~1GB RAM, fastest, lowest quality
- `base`: ~1GB RAM, good for most use cases
- `small`: ~2GB RAM, better quality
- `medium`: ~5GB RAM, high quality
- `large`: ~10GB RAM, best quality (requires GPU)

### Using Ollama for Local LLM

Run LLMs locally with Ollama:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3

# Configure in .env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

### Scheduled Processing & Weekly Emails

Use the included setup script for easy automation:

```bash
./setup_cron.sh
```

This will help you set up:
- **Daily processing**: Automatically sync and process new episodes (2 AM daily)
- **Weekly email digest**: Send summary emails every Saturday morning (8 AM)

Or manually add to crontab (`crontab -e`):

```bash
# Daily podcast processing at 2 AM
0 2 * * * cd /path/to/podripper && /path/to/venv/bin/python podripper.py run

# Weekly email digest every Saturday at 8 AM
0 8 * * SAT cd /path/to/podripper && /path/to/venv/bin/python podripper.py send-email
```

## Troubleshooting

### Audio Download Fails

- Ensure ffmpeg is installed: `ffmpeg -version`
- Check the audio URL is accessible
- Some feeds may require specific user agents

### Transcription is Slow

- Use a smaller Whisper model (`tiny` or `base`)
- Use GPU acceleration if available
- Consider using OpenAI's API for faster processing

### Out of Memory

- Reduce `max_tokens` in config
- Use smaller Whisper model
- Process fewer episodes at once (`max_episodes_per_run`)

### API Rate Limits

- Reduce `concurrent_workers` to 1
- Add delays between requests (edit orchestrator.py)
- Monitor your API usage

## Database Schema

The system uses DuckDB with the following tables:

- `feeds`: Podcast feed information
- `episodes`: Episode metadata
- `processing_status`: Processing state for each episode
- `transcripts`: Raw and cleaned transcripts
- `summaries`: Structured summary data
- `processing_logs`: Detailed processing logs

## Contributing

Contributions are welcome! Areas for improvement:

- Speaker diarization (identify different speakers)
- Multi-language support
- Web interface for browsing summaries
- Integration with note-taking apps
- Automated social media posting

## License

MIT License - See LICENSE file for details

## Acknowledgments

- OpenAI Whisper for transcription
- Anthropic Claude for intelligent text processing
- yt-dlp for robust audio downloading
- DuckDB for efficient data storage

## Support

For issues or questions:
- Check logs in `data/podripper.log`
- Review episode status: `python podripper.py stats`
- Check processing logs in the database
