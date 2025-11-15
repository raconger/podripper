#!/usr/bin/env python3
"""
PodRipper - Podcast Processing & Summarization System

Main CLI entry point for the podcast processing system.
"""

import sys
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table

from src.utils import ConfigManager, setup_logging
from src.orchestrator import PodcastOrchestrator
from src.audio import OPMLParser
from src.email import EmailSender, WeeklySummaryGenerator


console = Console()


@click.group()
@click.option('--config', default='config.yaml', help='Path to config file')
@click.option('--env', default='.env', help='Path to .env file')
@click.option('--log-level', default='INFO', help='Logging level')
@click.pass_context
def cli(ctx, config, env, log_level):
    """PodRipper - Podcast Processing & Summarization System"""
    ctx.ensure_object(dict)

    # Setup logging
    config_manager = ConfigManager(config_path=config, env_path=env)
    setup_logging(
        log_level=log_level,
        log_file=config_manager.env['log_file']
    )

    ctx.obj['config'] = config_manager
    ctx.obj['orchestrator'] = PodcastOrchestrator(config_manager)


@cli.command()
@click.pass_context
def sync(ctx):
    """Sync podcast feeds and add new episodes to the database."""
    orchestrator = ctx.obj['orchestrator']

    console.print("[bold blue]Syncing podcast feeds...[/bold blue]")

    new_episodes = orchestrator.sync_feeds()

    if new_episodes > 0:
        console.print(f"[green]✓ Added {new_episodes} new episodes[/green]")
    else:
        console.print("[yellow]No new episodes found[/yellow]")


@cli.command()
@click.option('--limit', default=None, type=int, help='Max episodes to process')
@click.option('--episode-id', default=None, type=int, help='Process specific episode ID')
@click.pass_context
def process(ctx, limit, episode_id):
    """Process pending episodes through the complete pipeline."""
    orchestrator = ctx.obj['orchestrator']

    if episode_id:
        console.print(f"[bold blue]Processing episode ID: {episode_id}[/bold blue]")
        success = orchestrator.process_episode(episode_id)

        if success:
            console.print("[green]✓ Episode processed successfully[/green]")
        else:
            console.print("[red]✗ Episode processing failed[/red]")
            sys.exit(1)
    else:
        console.print("[bold blue]Processing pending episodes...[/bold blue]")
        orchestrator.process_pending_episodes(limit=limit)


@cli.command()
@click.pass_context
def run(ctx):
    """Run complete workflow: sync feeds and process episodes."""
    orchestrator = ctx.obj['orchestrator']

    console.print("[bold blue]Running complete workflow...[/bold blue]\n")

    # Step 1: Sync feeds
    console.print("[bold]Step 1:[/bold] Syncing feeds...")
    new_episodes = orchestrator.sync_feeds()
    console.print(f"[green]✓ Added {new_episodes} new episodes[/green]\n")

    # Step 2: Process episodes
    console.print("[bold]Step 2:[/bold] Processing episodes...")
    orchestrator.process_pending_episodes()

    # Step 3: Show stats
    console.print("\n[bold]Processing Statistics:[/bold]")
    stats = orchestrator.get_stats()

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right")

    table.add_row("Total Episodes", str(stats['total_episodes']))
    table.add_row("Completed", str(stats['completed']), style="green")
    table.add_row("Pending", str(stats['pending']), style="yellow")
    table.add_row("In Progress", str(stats['in_progress']), style="blue")
    table.add_row("Failed", str(stats['failed']), style="red")

    console.print(table)


@cli.command()
@click.pass_context
def stats(ctx):
    """Show processing statistics."""
    orchestrator = ctx.obj['orchestrator']

    stats = orchestrator.get_stats()

    table = Table(show_header=True, header_style="bold magenta", title="Processing Statistics")
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right")

    table.add_row("Total Episodes", str(stats['total_episodes']))
    table.add_row("Completed", str(stats['completed']), style="green")
    table.add_row("Pending", str(stats['pending']), style="yellow")
    table.add_row("In Progress", str(stats['in_progress']), style="blue")
    table.add_row("Failed", str(stats['failed']), style="red")

    console.print(table)


@cli.command()
@click.argument('feed_name')
@click.argument('feed_url')
@click.option('--enabled/--disabled', default=True, help='Enable or disable the feed')
@click.pass_context
def add_feed(ctx, feed_name, feed_url, enabled):
    """Add a new podcast feed."""
    orchestrator = ctx.obj['orchestrator']

    feed_id = orchestrator.db.add_feed(feed_name, feed_url, enabled)

    if feed_id:
        console.print(f"[green]✓ Feed '{feed_name}' added (ID: {feed_id})[/green]")
    else:
        console.print("[yellow]Feed already exists[/yellow]")


@cli.command()
@click.pass_context
def list_feeds(ctx):
    """List all enabled feeds."""
    orchestrator = ctx.obj['orchestrator']

    feeds = orchestrator.db.get_enabled_feeds()

    if not feeds:
        console.print("[yellow]No enabled feeds found[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta", title="Enabled Feeds")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("URL")
    table.add_column("Last Checked")

    for feed in feeds:
        table.add_row(
            str(feed['id']),
            feed['name'],
            feed['url'][:50] + "..." if len(feed['url']) > 50 else feed['url'],
            str(feed['last_checked']) if feed['last_checked'] else "Never"
        )

    console.print(table)


@cli.command()
@click.option('--status', default='all', help='Filter by status (all, pending, completed, failed)')
@click.option('--limit', default=10, type=int, help='Number of episodes to show')
@click.pass_context
def list_episodes(ctx, status, limit):
    """List episodes."""
    orchestrator = ctx.obj['orchestrator']

    if status == 'pending':
        episodes = orchestrator.db.get_pending_episodes(limit=limit)
    else:
        # Get all episodes
        with orchestrator.db.get_connection() as conn:
            query = """
            SELECT e.id, e.title, e.published_date, ps.status
            FROM episodes e
            JOIN processing_status ps ON e.id = ps.episode_id
            """
            if status != 'all':
                query += f" WHERE ps.status = '{status}'"
            query += f" ORDER BY e.published_date DESC LIMIT {limit}"

            results = conn.execute(query).fetchall()
            episodes = [
                {
                    'id': r[0],
                    'title': r[1],
                    'published_date': r[2],
                    'status': r[3]
                }
                for r in results
            ]

    if not episodes:
        console.print(f"[yellow]No episodes found with status: {status}[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta", title="Episodes")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Published", style="blue")
    table.add_column("Status")

    for ep in episodes:
        status_style = {
            'completed': 'green',
            'failed': 'red',
            'pending': 'yellow',
        }.get(ep['status'], 'white')

        table.add_row(
            str(ep['id']),
            ep['title'][:60] + "..." if len(ep['title']) > 60 else ep['title'],
            str(ep.get('published_date', 'N/A'))[:10],
            f"[{status_style}]{ep['status']}[/{status_style}]"
        )

    console.print(table)


@cli.command()
@click.argument('opml_file', type=click.Path(exists=True))
@click.option('--enable-all/--no-enable', default=True, help='Enable all imported feeds')
@click.pass_context
def import_opml(ctx, opml_file, enable_all):
    """Import podcast feeds from an OPML file."""
    orchestrator = ctx.obj['orchestrator']

    console.print(f"[bold blue]Importing feeds from {opml_file}...[/bold blue]")

    # Parse OPML
    feeds = OPMLParser.parse_opml(opml_file)

    if not feeds:
        console.print("[red]✗ Failed to parse OPML file or no feeds found[/red]")
        sys.exit(1)

    # Validate feeds
    valid_feeds = OPMLParser.validate_feeds(feeds)

    console.print(f"Found {len(valid_feeds)} valid feeds\n")

    # Add feeds to database
    added_count = 0
    skipped_count = 0

    for feed in valid_feeds:
        feed_id = orchestrator.db.add_feed(
            name=feed['name'],
            url=feed['url'],
            enabled=enable_all
        )

        if feed_id:
            console.print(f"[green]✓ Added:[/green] {feed['name']}")
            added_count += 1
        else:
            console.print(f"[yellow]⊙ Exists:[/yellow] {feed['name']}")
            skipped_count += 1

    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Added: {added_count}")
    console.print(f"  Skipped (already exists): {skipped_count}")


@cli.command()
@click.option('--output', '-o', default='feeds.opml', help='Output OPML file path')
@click.pass_context
def export_opml(ctx, output):
    """Export podcast feeds to an OPML file."""
    orchestrator = ctx.obj['orchestrator']

    console.print("[bold blue]Exporting feeds to OPML...[/bold blue]")

    feeds = orchestrator.db.get_enabled_feeds()

    if not feeds:
        console.print("[yellow]No enabled feeds to export[/yellow]")
        sys.exit(1)

    # Convert to OPML format
    opml_feeds = [
        {'name': f['name'], 'url': f['url']}
        for f in feeds
    ]

    # Export
    success = OPMLParser.export_opml(opml_feeds, output)

    if success:
        console.print(f"[green]✓ Exported {len(feeds)} feeds to {output}[/green]")
    else:
        console.print(f"[red]✗ Failed to export OPML[/red]")
        sys.exit(1)


@cli.command()
@click.option('--days', default=7, help='Number of days to include in digest')
@click.option('--test', is_flag=True, help='Send test email')
@click.pass_context
def send_email(ctx, days, test):
    """Send weekly podcast digest email."""
    config = ctx.obj['config']
    orchestrator = ctx.obj['orchestrator']

    # Check if email is configured
    if not config.env['email_to'] or not config.env['smtp_username']:
        console.print("[red]✗ Email not configured. Please set EMAIL_TO and SMTP_USERNAME in .env[/red]")
        sys.exit(1)

    console.print("[bold blue]Generating weekly email digest...[/bold blue]")

    # Initialize email components
    email_sender = EmailSender(
        smtp_server=config.env['smtp_server'],
        smtp_port=config.env['smtp_port'],
        username=config.env['smtp_username'],
        password=config.env['smtp_password'],
        from_email=config.env['email_from'],
        use_tls=True
    )

    summary_generator = WeeklySummaryGenerator(orchestrator.db)

    # Get episodes
    episodes = summary_generator.get_weekly_episodes(days=days)

    if not episodes:
        console.print(f"[yellow]No episodes processed in the last {days} days[/yellow]")
        if not test:
            sys.exit(0)

    console.print(f"Found {len(episodes)} episodes to include")

    # Generate email content
    include_full = config.config.email.include_full_summaries
    html_body = summary_generator.generate_html_email(episodes, include_full_summaries=include_full)
    text_body = summary_generator.generate_text_email(episodes)

    # Send email
    console.print(f"Sending email to {config.env['email_to']}...")

    success = email_sender.send_email(
        to_email=config.env['email_to'],
        subject=config.env['email_subject'] + (" (Test)" if test else ""),
        body_html=html_body,
        body_text=text_body
    )

    if success:
        console.print("[green]✓ Email sent successfully[/green]")
    else:
        console.print("[red]✗ Failed to send email[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def test_email(ctx):
    """Test email configuration."""
    config = ctx.obj['config']

    console.print("[bold blue]Testing email configuration...[/bold blue]")

    # Check configuration
    if not config.env['smtp_username'] or not config.env['smtp_password']:
        console.print("[red]✗ SMTP credentials not configured in .env[/red]")
        sys.exit(1)

    # Initialize email sender
    email_sender = EmailSender(
        smtp_server=config.env['smtp_server'],
        smtp_port=config.env['smtp_port'],
        username=config.env['smtp_username'],
        password=config.env['smtp_password'],
        from_email=config.env['email_from'],
        use_tls=True
    )

    # Test connection
    success = email_sender.test_connection()

    if success:
        console.print("[green]✓ Email configuration is valid[/green]")
        console.print(f"  Server: {config.env['smtp_server']}:{config.env['smtp_port']}")
        console.print(f"  From: {config.env['email_from']}")
    else:
        console.print("[red]✗ Email configuration test failed[/red]")
        console.print("  Check your SMTP credentials and server settings")
        sys.exit(1)


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize configuration files."""
    console.print("[bold blue]Initializing PodRipper...[/bold blue]\n")

    # Check if config files exist
    config_path = Path('config.yaml')
    env_path = Path('.env')

    if config_path.exists():
        console.print("[yellow]config.yaml already exists[/yellow]")
    else:
        # Copy template
        template_path = Path('config.yaml.template')
        if template_path.exists():
            import shutil
            shutil.copy(template_path, config_path)
            console.print("[green]✓ Created config.yaml from template[/green]")
        else:
            console.print("[red]✗ config.yaml.template not found[/red]")

    if env_path.exists():
        console.print("[yellow].env already exists[/yellow]")
    else:
        # Copy template
        template_path = Path('.env.template')
        if template_path.exists():
            import shutil
            shutil.copy(template_path, env_path)
            console.print("[green]✓ Created .env from template[/green]")
        else:
            console.print("[red]✗ .env.template not found[/red]")

    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Edit .env and add your API keys")
    console.print("2. Edit config.yaml and configure your podcast feeds")
    console.print("3. Or import feeds: python podripper.py import-opml your_feeds.opml")
    console.print("4. Run: python podripper.py sync")
    console.print("5. Run: python podripper.py process")


if __name__ == '__main__':
    cli()
