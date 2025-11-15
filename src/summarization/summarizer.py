"""
Podcast summarization module using LLMs.
"""

import json
from typing import Optional, Dict, Any
from pathlib import Path
from loguru import logger
import anthropic
from openai import OpenAI


SUMMARIZATION_PROMPT = """You are an expert podcast analyst. Analyze the following podcast transcript and create a comprehensive structured summary.

Generate a summary with the following sections:

1. **Host and Guest**: Identify the host(s) and guest(s) with brief context about who they are (titles, companies, expertise)

2. **Comprehensive Summary**: Provide a high-level overview of the episode in 2-3 well-crafted paragraphs that captures the main themes and flow of conversation

3. **Key Topics and Themes**: List the main discussion points, organized by category or theme. For each topic, provide a brief explanation (2-3 sentences)

4. **Actionable Quotes**: Extract 5-10 notable, insightful, or memorable quotes. For each quote:
   - Include the exact quote
   - Attribute it to the speaker
   - Provide brief context about what was being discussed

5. **Investment Theses**: Identify any potential market opportunities, trends, or investment ideas discussed. For each:
   - State the thesis clearly
   - Summarize the reasoning presented
   - Note any risks or counterarguments mentioned

6. **Noteworthy Observations**: Extract 3-5 unique insights, perspectives, or observations that would make compelling social media posts or discussion points

7. **Company Mentions**: List all startups, companies, or organizations mentioned with:
   - Company name
   - Industry/sector
   - Context of why they were discussed
   - Any specific details shared (funding, metrics, strategies, etc.)

Format your response as JSON with this structure:
{
  "host_and_guest": "text",
  "comprehensive_summary": "text",
  "key_topics": [
    {"topic": "topic name", "description": "description"}
  ],
  "actionable_quotes": [
    {"quote": "exact quote", "speaker": "name", "context": "context"}
  ],
  "investment_theses": [
    {"thesis": "thesis statement", "reasoning": "reasoning", "risks": "risks or caveats"}
  ],
  "noteworthy_observations": [
    "observation 1",
    "observation 2"
  ],
  "company_mentions": [
    {"name": "company name", "industry": "industry", "context": "context", "details": "specific details"}
  ]
}

IMPORTANT: Return ONLY valid JSON, no markdown formatting or code blocks.

Transcript:
{transcript}"""


class PodcastSummarizer:
    """Generate structured summaries of podcast episodes."""

    def __init__(
        self,
        provider: str = "anthropic",
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 4000
    ):
        """
        Initialize the summarizer.

        Args:
            provider: LLM provider (anthropic, openai, ollama)
            model: Model name
            api_key: API key for cloud providers
            base_url: Base URL for Ollama
            temperature: Sampling temperature
            max_tokens: Maximum tokens per request
        """
        self.provider = provider.lower()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize client based on provider
        if self.provider == "anthropic":
            if not api_key:
                raise ValueError("API key required for Anthropic")
            self.client = anthropic.Anthropic(api_key=api_key)
            logger.info(f"Initialized Anthropic summarizer with model: {model}")

        elif self.provider == "openai":
            if not api_key:
                raise ValueError("API key required for OpenAI")
            self.client = OpenAI(api_key=api_key)
            logger.info(f"Initialized OpenAI summarizer with model: {model}")

        elif self.provider == "ollama":
            base_url = base_url or "http://localhost:11434"
            self.client = OpenAI(base_url=f"{base_url}/v1", api_key="ollama")
            logger.info(f"Initialized Ollama summarizer with model: {model}")

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def summarize(self, transcript: str) -> Optional[Dict[str, Any]]:
        """
        Generate a structured summary of a podcast transcript.

        Args:
            transcript: Cleaned transcript text

        Returns:
            Dictionary with structured summary
        """
        if not transcript or not transcript.strip():
            logger.warning("Empty transcript provided")
            return None

        try:
            prompt = SUMMARIZATION_PROMPT.format(transcript=transcript)

            logger.info(f"Generating summary using {self.provider}/{self.model}")

            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                summary_text = response.content[0].text

            elif self.provider in ["openai", "ollama"]:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                summary_text = response.choices[0].message.content

            else:
                logger.error(f"Unsupported provider: {self.provider}")
                return None

            # Parse JSON response
            # Remove markdown code blocks if present
            summary_text = summary_text.strip()
            if summary_text.startswith('```'):
                # Remove code block markers
                lines = summary_text.split('\n')
                summary_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else summary_text

            summary_data = json.loads(summary_text)

            logger.info("Summary generated successfully")
            return summary_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse summary JSON: {e}")
            logger.error(f"Raw response: {summary_text[:500]}")
            return None

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return None

    def summarize_to_markdown(self, transcript: str) -> Optional[str]:
        """
        Generate a summary and format as Markdown.

        Args:
            transcript: Cleaned transcript text

        Returns:
            Markdown formatted summary
        """
        summary = self.summarize(transcript)

        if not summary:
            return None

        # Format as Markdown
        md_lines = ["# Podcast Summary\n"]

        # Host and Guest
        md_lines.append("## Host and Guest\n")
        md_lines.append(f"{summary.get('host_and_guest', 'N/A')}\n")

        # Comprehensive Summary
        md_lines.append("## Comprehensive Summary\n")
        md_lines.append(f"{summary.get('comprehensive_summary', 'N/A')}\n")

        # Key Topics
        md_lines.append("## Key Topics and Themes\n")
        for topic in summary.get('key_topics', []):
            md_lines.append(f"### {topic.get('topic', 'Unknown Topic')}\n")
            md_lines.append(f"{topic.get('description', '')}\n")

        # Actionable Quotes
        md_lines.append("## Actionable Quotes\n")
        for i, quote in enumerate(summary.get('actionable_quotes', []), 1):
            md_lines.append(f"### Quote {i}\n")
            md_lines.append(f"> \"{quote.get('quote', '')}\"\n")
            md_lines.append(f"**— {quote.get('speaker', 'Unknown')}**\n")
            md_lines.append(f"*Context: {quote.get('context', '')}*\n")

        # Investment Theses
        md_lines.append("## Investment Theses\n")
        for i, thesis in enumerate(summary.get('investment_theses', []), 1):
            md_lines.append(f"### Thesis {i}: {thesis.get('thesis', 'N/A')}\n")
            md_lines.append(f"**Reasoning:** {thesis.get('reasoning', '')}\n")
            if thesis.get('risks'):
                md_lines.append(f"**Risks/Caveats:** {thesis.get('risks', '')}\n")

        # Noteworthy Observations
        md_lines.append("## Noteworthy Observations\n")
        for obs in summary.get('noteworthy_observations', []):
            md_lines.append(f"- {obs}\n")

        # Company Mentions
        md_lines.append("## Company Mentions\n")
        for company in summary.get('company_mentions', []):
            md_lines.append(f"### {company.get('name', 'Unknown Company')}\n")
            md_lines.append(f"**Industry:** {company.get('industry', 'N/A')}\n")
            md_lines.append(f"**Context:** {company.get('context', '')}\n")
            if company.get('details'):
                md_lines.append(f"**Details:** {company.get('details', '')}\n")

        return '\n'.join(md_lines)

    def summarize_file(
        self,
        input_path: str,
        output_format: str = "both",
        output_dir: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Summarize a transcript file and save output.

        Args:
            input_path: Path to transcript file
            output_format: Output format (json, markdown, both)
            output_dir: Directory to save output files

        Returns:
            Summary data dictionary
        """
        try:
            # Read transcript
            input_file = Path(input_path)
            if not input_file.exists():
                logger.error(f"Input file not found: {input_path}")
                return None

            transcript = input_file.read_text(encoding='utf-8')

            # Generate summary
            summary_data = self.summarize(transcript)

            if not summary_data:
                return None

            # Determine output paths
            if output_dir:
                output_base = Path(output_dir) / input_file.stem
            else:
                output_base = input_file.parent / input_file.stem

            output_base.parent.mkdir(parents=True, exist_ok=True)

            # Save JSON
            if output_format in ["json", "both"]:
                json_path = output_base.with_suffix('.json')
                json_path.write_text(
                    json.dumps(summary_data, indent=2, ensure_ascii=False),
                    encoding='utf-8'
                )
                logger.info(f"Summary JSON saved to: {json_path}")

            # Save Markdown
            if output_format in ["markdown", "both"]:
                markdown_text = self.summarize_to_markdown(transcript)
                if markdown_text:
                    md_path = output_base.with_suffix('.md')
                    md_path.write_text(markdown_text, encoding='utf-8')
                    logger.info(f"Summary Markdown saved to: {md_path}")

            return summary_data

        except Exception as e:
            logger.error(f"Failed to summarize file {input_path}: {e}")
            return None

    def get_summarizer_info(self) -> dict:
        """Get information about the summarizer configuration."""
        return {
            'provider': self.provider,
            'model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }
