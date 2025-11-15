# PodRipper Quick Start Guide

Get up and running with PodRipper in 5 minutes!

## 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Install ffmpeg (if not already installed)
# Ubuntu/Debian:
sudo apt-get install ffmpeg

# macOS:
brew install ffmpeg
```

## 2. Initialize Configuration

```bash
python podripper.py init
```

## 3. Configure API Keys

Edit `.env` and add at least one API key:

```bash
# Recommended: Claude for best quality
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Or use OpenAI
OPENAI_API_KEY=sk-xxxxx

# Choose provider
LLM_PROVIDER=anthropic
```

## 4. Add Podcast Feeds

Edit `config.yaml` to add your favorite podcasts:

```yaml
feeds:
  - name: "Lex Fridman Podcast"
    url: "https://lexfridman.com/feed/podcast/"
    enabled: true
```

## 5. Run!

```bash
# Sync feeds and process episodes
python podripper.py run
```

That's it! Your summaries will be in `data/summaries/`.

## What Happens Next?

1. **Sync**: Downloads feed metadata, finds new episodes
2. **Download**: Downloads episode audio files
3. **Transcribe**: Converts audio to text using Whisper
4. **Clean**: Removes filler words using AI
5. **Summarize**: Generates structured summary

## Viewing Results

```bash
# Check status
python podripper.py stats

# List episodes
python podripper.py list-episodes

# View summaries
cat data/summaries/1_summary.md
```

## Common Commands

```bash
# Sync feeds only
python podripper.py sync

# Process specific episode
python podripper.py process --episode-id 1

# Process limited number
python podripper.py process --limit 3
```

## Tips

- Start with `WHISPER_MODEL=base` for speed
- Use `max_episodes_per_run: 2` for testing
- Check `data/podripper.log` if issues occur
- Summaries work best with Claude or GPT-4

## Need Help?

- Check logs: `tail -f data/podripper.log`
- View stats: `python podripper.py stats`
- Read full docs: [README.md](README.md)
