# OPML Import Guide

OPML (Outline Processor Markup Language) is the standard format used by podcast apps to export and import podcast subscriptions. PodRipper supports importing your podcast subscriptions from any podcast app via OPML files.

## Exporting OPML from Popular Podcast Apps

### Apple Podcasts (macOS)
1. Open Apple Podcasts
2. Go to File → Export Subscriptions
3. Save the file (e.g., `podcasts.opml`)

### Overcast (iOS)
1. Open Overcast
2. Go to Settings → OPML Export
3. Share or save the OPML file
4. Transfer to your computer via AirDrop or email

### Pocket Casts
1. Open Pocket Casts web version (https://play.pocketcasts.com)
2. Go to Settings → Import/Export
3. Click "Export" to download OPML file

### Castro
1. Open Castro
2. Go to Settings → Export OPML
3. Share the file via email or AirDrop

### Spotify
Note: Spotify doesn't natively support OPML export. You'll need to manually add feeds or use a third-party tool.

### Podcast Addict (Android)
1. Open Podcast Addict
2. Go to Settings → Backup
3. Export as OPML

### AntennaPod (Android)
1. Open AntennaPod
2. Go to Settings → Storage → Import/Export
3. Export Database (includes OPML)

## Importing OPML to PodRipper

Once you have your OPML file:

```bash
# Import and enable all feeds
python podripper.py import-opml podcasts.opml

# Import but don't enable feeds automatically
python podripper.py import-opml podcasts.opml --no-enable
```

## What Gets Imported

From the OPML file, PodRipper extracts:
- **Feed name**: The podcast title
- **Feed URL**: The RSS feed URL
- **Description**: Podcast description (if available)
- **Website**: HTML URL (if available)

## After Import

1. **View imported feeds:**
   ```bash
   python podripper.py list-feeds
   ```

2. **Sync to get episodes:**
   ```bash
   python podripper.py sync
   ```

3. **Start processing:**
   ```bash
   python podripper.py process
   ```

## Exporting OPML

You can also export your PodRipper feeds to OPML:

```bash
# Export to default location (feeds.opml)
python podripper.py export-opml

# Export to specific file
python podripper.py export-opml --output my-podcasts.opml
```

This is useful for:
- Backing up your feed list
- Importing to another podcast app
- Sharing your podcast subscriptions

## Troubleshooting

### "No feeds found in OPML file"
- Ensure the OPML file is valid XML
- Some apps export multiple file types - make sure you selected OPML
- Try opening the file in a text editor to verify it contains `<outline>` elements

### "Failed to parse OPML file"
- The file may be corrupted
- Re-export from your podcast app
- Ensure the file wasn't converted to a different format during transfer

### Feeds imported but not processing
- Check feed status: `python podripper.py list-feeds`
- Enable feeds if they were imported as disabled
- Run sync to fetch episodes: `python podripper.py sync`

## OPML File Format

Example OPML structure:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head>
    <title>My Podcasts</title>
  </head>
  <body>
    <outline text="Lex Fridman Podcast"
             type="rss"
             xmlUrl="https://lexfridman.com/feed/podcast/"
             htmlUrl="https://lexfridman.com" />
    <outline text="All-In Podcast"
             type="rss"
             xmlUrl="https://feeds.megaphone.fm/allin" />
  </body>
</opml>
```

PodRipper looks for `<outline>` elements with `xmlUrl` attributes and treats them as podcast feeds.
