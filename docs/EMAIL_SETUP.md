#!/# Weekly Email Digest Setup Guide

PodRipper can automatically send you a beautiful HTML email digest every Saturday morning with summaries of all podcasts processed during the week.

## Quick Setup

### 1. Configure Email Settings in `.env`

Edit your `.env` file and add:

```bash
# Enable email
EMAIL_ENABLED=true

# SMTP Server (examples below for common providers)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Your email credentials
SMTP_USERNAME=your.email@gmail.com
SMTP_PASSWORD=your_app_password  # See below for app passwords

# Email addresses
EMAIL_FROM=your.email@gmail.com
EMAIL_TO=recipient@example.com

# Email subject
EMAIL_SUBJECT=Your Weekly Podcast Digest
```

### 2. Get App-Specific Password

For security, most email providers require app-specific passwords (not your regular password).

#### Gmail
1. Go to your Google Account settings
2. Navigate to Security → 2-Step Verification
3. Scroll down to "App passwords"
4. Generate a new app password for "Mail"
5. Use this password in `SMTP_PASSWORD`

**Settings:**
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

#### Outlook/Hotmail
1. Go to account.microsoft.com
2. Security → Advanced security options
3. Create app password
4. Use in `SMTP_PASSWORD`

**Settings:**
```bash
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
```

#### Yahoo Mail
1. Go to Account Security
2. Generate app password
3. Use in `SMTP_PASSWORD`

**Settings:**
```bash
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
```

#### Custom SMTP Server
```bash
SMTP_SERVER=mail.yourdomain.com
SMTP_PORT=587  # or 465 for SSL
SMTP_USERNAME=your.email@yourdomain.com
SMTP_PASSWORD=your_password
```

### 3. Test Email Configuration

Before setting up automation, test your email settings:

```bash
# Test SMTP connection
python podripper.py test-email

# Send a test digest email
python podripper.py send-email --test
```

If successful, you'll see:
```
✓ Email sent successfully
```

## Setting Up Weekly Emails

### Option 1: Automated with Cron (Recommended)

Use the included setup script:

```bash
./setup_cron.sh
```

Choose option 2 or 3 to enable weekly emails.

This will schedule the email to be sent every Saturday at 8 AM.

### Option 2: Manual Cron Setup

Edit your crontab:

```bash
crontab -e
```

Add this line (adjust paths to match your installation):

```bash
# Send weekly podcast digest every Saturday at 8 AM
0 8 * * SAT cd /path/to/podripper && /path/to/venv/bin/python podripper.py send-email >> data/cron.log 2>&1
```

### Option 3: Manual Trigger

Send email digest manually anytime:

```bash
# Send digest of last 7 days
python podripper.py send-email

# Send digest of last 14 days
python podripper.py send-email --days 14
```

## Email Content

The weekly digest includes:

### 📧 Email Header
- Title: "Your Weekly Podcast Digest"
- Date range covered
- Number of episodes processed

### 📝 Table of Contents
- Quick links to each episode summary

### 🎧 For Each Episode
1. **Title and Metadata**: Podcast name, date
2. **Host and Guest**: Who was on the show
3. **Summary**: High-level overview (2-3 paragraphs)
4. **Top Quotes**: Best quotes with context (limited to 3 in email)
5. **Key Topics**: Main discussion points
6. **Companies Mentioned**: Relevant companies and context
7. **Investment Theses**: Market opportunities discussed (if enabled)

## Customizing Email Content

Edit `config.yaml`:

```yaml
email:
  enabled: true

  # When to send (cron format)
  schedule: "0 8 * * SAT"  # Saturday 8 AM

  # How many days to include
  days_to_include: 7

  # Include full summaries or just highlights
  include_full_summaries: false  # Set to true for more detail
```

### Email Frequency Options

Change the schedule in your cron job:

```bash
# Every Monday at 9 AM
0 9 * * MON cd /path/to/podripper && python podripper.py send-email

# Every Sunday at 7 PM
0 19 * * SUN cd /path/to/podripper && python podripper.py send-email

# Bi-weekly (every other Saturday)
0 8 */14 * SAT cd /path/to/podripper && python podripper.py send-email --days 14
```

## Troubleshooting

### "SMTP authentication failed"
- **Cause**: Wrong password or app password not set up
- **Fix**: Generate an app-specific password (see above)
- **Gmail users**: Ensure 2FA is enabled first

### "Email not configured"
- **Cause**: Missing `EMAIL_TO` or `SMTP_USERNAME` in `.env`
- **Fix**: Add all required email settings to `.env`

### "Connection timeout"
- **Cause**: Wrong SMTP server or port, or firewall blocking
- **Fix**:
  - Verify SMTP server and port for your provider
  - Try port 465 instead of 587
  - Check firewall settings

### Email sent but not received
- **Check spam folder**: First email might be flagged
- **Verify EMAIL_TO address**: Make sure it's correct
- **Check email logs**: Look in `data/podripper.log`

### "No episodes processed this week"
- **Normal**: If no podcasts were processed in the last 7 days
- **Check processing**: Run `python podripper.py stats`
- **Process episodes**: Run `python podripper.py run`

## Sample Email Preview

Here's what your email will look like:

```
╔══════════════════════════════════════╗
║   🎧 Your Weekly Podcast Digest      ║
║   November 8 - November 15, 2024     ║
║   3 episodes processed this week     ║
╚══════════════════════════════════════╝

This Week's Episodes
├─ Episode 1: AI and the Future of Work
├─ Episode 2: Startup Funding in 2024
└─ Episode 3: Climate Tech Innovations

[Full summaries with quotes, topics, companies...]
```

## Advanced: Custom Email Templates

To customize the email HTML, edit:
```
src/email/summary_generator.py
```

Look for the `_get_html_header()` method to modify styles and layout.

## Privacy & Security

- **Passwords**: Never commit `.env` file to git
- **App Passwords**: More secure than your main password
- **Local Processing**: Emails generated locally, not sent to third parties
- **SMTP over TLS**: All email transmission is encrypted

## Getting Help

Test each step:

```bash
# 1. Test SMTP connection
python podripper.py test-email

# 2. Send test email
python podripper.py send-email --test

# 3. Check logs
tail -f data/podripper.log

# 4. View cron jobs
crontab -l
```

If you need help, check the logs in `data/podripper.log` and `data/cron.log`.
