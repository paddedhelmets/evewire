"""
Markdown fitting format parser.

Extracts EFT-format fittings from markdown files with metadata.
Format used by clustering output: representative fits with metadata.

Example format:
    # Ship Name - Cluster N

    ## Representative Fit (X fits in cluster)

    **Fit ID**: 1234567
    **Killmail**: [123456789](https://zkillboard.com/kill/123456789/)

    ```
    [Ship, Fit Name]
    Module1
    Module2
    ...
    ```

    ### Cluster Samples

    | Fit ID | Killmail ID | Zkillboard |
    ...
"""

import re
from typing import Dict, List, Tuple, Optional
from .base import FittingData, FittingParser


class MarkdownParser(FittingParser):
    """
    Parser for markdown-format fittings.

    Extracts EFT-format fittings from markdown code blocks while
    preserving metadata as tags and using remaining content as description.
    """

    def validate(self, content: str) -> bool:
        """
        Validate content appears to be markdown format with fitting.

        Args:
            content: Content to validate

        Returns:
            True if content has markdown heading and code block with EFT fit
        """
        content = content.strip()
        # Check for markdown heading (#)
        if not content.startswith('#'):
            return False
        # Check for code block
        if '```' not in content:
            return False
        # Check for EFT-style fit in code block
        eft_content = self._extract_eft_block(content)
        if not eft_content:
            return False
        # Check EFT content has [Ship, Name] format
        lines = eft_content.split('\n')
        if not lines or not (lines[0].startswith('[') and ']' in lines[0] and ',' in lines[0]):
            return False
        return True

    def parse(self, content: str) -> FittingData:
        """
        Parse markdown content to extract fitting data.

        Args:
            content: Markdown content with embedded EFT fit

        Returns:
            FittingData with extracted fit, metadata, and description

        Raises:
            InvalidFormatError: If markdown format is invalid
            ItemNotFoundError: If ship type not found in SDE
        """
        from .exceptions import InvalidFormatError, ItemNotFoundError
        from .utils import resolve_item_name

        # Extract title (ship name + cluster)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if not title_match:
            raise InvalidFormatError("Missing markdown title (e.g., '# Ship - Cluster N')")

        title = title_match.group(1).strip()

        # Extract cluster number from title or filename
        cluster_match = re.search(r'Cluster\s+(\d+)', title)
        cluster_id = int(cluster_match.group(1)) if cluster_match else None

        # Extract fit count from "Representative Fit (X fits in cluster)"
        fit_count_match = re.search(r'\((\d+)\s+fits?\s+in\s+cluster\)', content)
        fit_count = int(fit_count_match.group(1)) if fit_count_match else None

        # Extract metadata fields (Fit ID, Killmail, etc.)
        metadata = self._extract_metadata(content)

        # Extract EFT fit from code block
        eft_content = self._extract_eft_block(content)
        if not eft_content:
            raise InvalidFormatError("No EFT fitting found in markdown code block")

        # Parse EFT format to get fitting data
        from .eft import EFTParser
        eft_parser = EFTParser()
        fitting_data = eft_parser.parse(eft_content)

        # Override name with markdown title if available
        if title:
            fitting_data.name = title

        # Build metadata dict
        metadata_dict = {
            'cluster_id': cluster_id,
            'fit_count': fit_count,
            'format': 'markdown',
        }
        metadata_dict.update(metadata)

        # Update fitting metadata
        if fitting_data.metadata is None:
            fitting_data.metadata = {}
        fitting_data.metadata.update(metadata_dict)

        # Extract description (everything after the code block, excluding metadata)
        fitting_data.description = self._extract_description(content)

        return fitting_data

    def _extract_metadata(self, content: str) -> Dict[str, str]:
        """Extract key-value metadata from markdown (**Key**: Value format)."""
        metadata = {}

        # Match **Key**: Value or **Key**: [Link](url) patterns
        pattern = r'\*\*([^*]+)\*\*:\s*(.+?)(?:\n|$)'
        for match in re.finditer(pattern, content):
            key = match.group(1).strip().lower().replace(' ', '_')
            value = match.group(2).strip()

            # Extract URL from markdown link if present
            link_match = re.match(r'\[([^\]]+)\]\(([^)]+)\)', value)
            if link_match:
                value = link_match.group(2)  # Use the URL

            metadata[key] = value

        return metadata

    def _extract_eft_block(self, content: str) -> Optional[str]:
        """Extract EFT fitting from markdown code block."""
        # Match ```code``` blocks
        pattern = r'```(?:\w+)?\n([\s\S]+?)```'
        matches = re.findall(pattern, content)

        # Return the first code block that looks like an EFT fit
        for match in matches:
            stripped = match.strip()
            if stripped.startswith('[') and ']' in stripped and ',' in stripped:
                return stripped

        return None

    def _extract_description(self, content: str) -> str:
        """
        Extract description from markdown content.

        Returns everything after the EFT code block (cluster samples,
        notes, etc.) as the description.
        """
        # Find the end of the first code block
        code_block_end = content.find('```', content.find('```') + 3)
        if code_block_end == -1:
            return ''

        # Get everything after the code block
        description_part = content[code_block_end + 3:].strip()

        # Remove leading whitespace and empty lines
        lines = description_part.split('\n')
        while lines and not lines[0].strip():
            lines.pop(0)

        return '\n'.join(lines).strip()


class MarkdownSerializer:
    """
    Serialize fitting data to markdown format.

    Not currently used for export, but available if needed.
    """

    def serialize(self, data: FittingData) -> str:
        """Serialize fitting data to markdown format."""
        from .eft import EFTSerializer

        # Build markdown structure
        lines = []

        # Title
        lines.append(f"# {data.name}")
        lines.append("")

        # Metadata section
        fit_count = data.metadata.get('fit_count')
        if fit_count:
            lines.append(f"## Representative Fit ({fit_count} fits in cluster)")
        else:
            lines.append("## Representative Fit")
        lines.append("")

        # Add metadata fields
        fit_id = data.metadata.get('fit_id')
        if fit_id:
            lines.append(f"**Fit ID**: {fit_id}")

        killmail = data.metadata.get('killmail')
        if killmail:
            lines.append(f"**Killmail**: [{killmail}](https://zkillboard.com/kill/{killmail}/)")

        if fit_id or killmail:
            lines.append("")

        # EFT fitting in code block
        eft_serializer = EFTSerializer()
        eft_content = eft_serializer.serialize(data)

        lines.append("```")
        lines.append(eft_content)
        lines.append("```")
        lines.append("")

        # Description
        if data.description:
            lines.append(data.description)
            lines.append("")

        return '\n'.join(lines)
