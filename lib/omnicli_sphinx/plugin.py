"""
Sphinx extension that provides a directive for generating CLI documentation from omni help output.
Parses JSON output from omni help command and creates structured documentation nodes.
"""

from docutils import nodes
from sphinx.util.docutils import SphinxDirective
import json
import subprocess


class OmniCLIDirective(SphinxDirective):
    """Directive that generates documentation from omni CLI help output."""

    has_content = False  # Directive doesn't accept content between tags
    required_arguments = 0  # No required arguments
    optional_arguments = float("inf")  # Accept unlimited optional arguments

    def run(self):
        """Execute omni help command and build documentation structure."""
        # Construct command to get help output in JSON format
        command = ["omni", "help", "-o", "json"]
        if self.arguments:
            command.extend(self.arguments)

        # Run the command, this will error out if omni is not available,
        # in a too old version for supporting the JSON output, or if the
        # command is not found.
        output = subprocess.check_output(command, text=True)
        data = json.loads(output)

        # Build main documentation section
        section = nodes.section(ids=["command"])

        # Add the command name as the title
        if "name" in data:
            section += nodes.title(text=f"omni {data["name"]}")
        elif not self.arguments:
            section += nodes.title(text="omni")

        # Add usage information if available
        if "usage" in data:
            section += nodes.literal_block(text=format_usage(data["usage"]))

        # Add command description, preferring full help over short help
        if "help" in data:
            section += nodes.paragraph(text=data["help"])
        elif "short_help" in data:
            section += nodes.paragraph(text=data["short_help"])

        # Create arguments section if command has arguments
        if "arguments" in data:
            args_section = nodes.section(ids=["arguments"])
            args_section += nodes.title(text="Arguments")
            args_list = nodes.option_list()
            for arg in data["arguments"]:
                args_list += nodes.option_list_item(
                    "",
                    nodes.option_group("", nodes.option_string(text=arg["name"])),
                    nodes.description("", nodes.paragraph(text=arg["desc"])),
                )
            args_section += args_list
            section += args_section

        # Create options section if command has options
        if "options" in data:
            opts_section = nodes.section(ids=["options"])
            opts_section += nodes.title(text="Options")
            opts_list = nodes.option_list()
            for opt in data["options"]:
                opts_list += nodes.option_list_item(
                    "",
                    nodes.option_group("", nodes.option_string(text=opt["name"])),
                    nodes.description("", nodes.paragraph(text=opt["desc"])),
                )
            opts_section += opts_list
            section += opts_section

        # Create subcommands section, grouped by category
        if "subcommands" in data:
            subcmds_section = nodes.section(ids=["subcommands"])
            subcmds_section += nodes.title(text="Subcommands")
            current_category = None

            subcmds_items = []
            for cmd in data["subcommands"]:
                categories = cmd.get("category", [])

                if not categories and current_category is not None:
                    categories = ["Uncategorized"]

                if categories and categories != current_category:
                    current_category = categories
                    categories.reverse()

                    # Make the first in the list strong, the rest normal
                    first = nodes.strong(text=categories[0].strip())
                    rest = [
                        (nodes.Text(" ← "), nodes.Text(category.strip()))
                        for category in categories[1:]
                    ]
                    # Flatten the list of tuples
                    rest = [item for sublist in rest for item in sublist]

                    if subcmds_items:
                        subcmds_section += nodes.definition_list("", *subcmds_items)
                        subcmds_items = []
                    subcmds_section += nodes.subtitle("", "", first, *rest)

                # Prepare the names of the subcommand
                names = [
                    nodes.strong(text=name.strip()) for name in cmd["name"].split(",")
                ]
                # Inject a ', ' between each name
                names = [(name, nodes.Text(", ")) for name in names[:-1]] + [
                    (names[-1],)
                ]
                # Flatten the list of tuples
                names = [item for sublist in names for item in sublist]

                item = nodes.definition_list_item()
                item += nodes.term("", "", *names)
                item += nodes.definition("", nodes.paragraph(text=cmd["desc"]))

                subcmds_items.append(item)

            if subcmds_items:
                subcmds_section += nodes.definition_list("", *subcmds_items)
            section += subcmds_section

        return [section]


def make_definition(term_text, def_text):
    """Helper function to create a definition list item with term and definition."""
    item = nodes.definition_list_item()
    term = nodes.term(text=term_text)
    definition = nodes.definition()
    definition += nodes.paragraph(text=def_text)
    item += [term, definition]
    return item


def split_respect_blocks(text):
    """
    Split text into parts while preserving blocks delimited by brackets.
    Blocks are sequences within matching [] or <> pairs.
    Returns list of parts.
    """
    parts = []
    blocks = []
    current = ""

    BLOCKS_CHARS = {"[": "]", "<": ">"}

    for char in text:
        # Handle block closing
        if blocks and char == blocks[-1]:
            blocks.pop()
            current += char
            if not blocks:
                if current:
                    parts.append(current)
                current = ""
            continue

        # Handle block opening
        if char in BLOCKS_CHARS:
            if not blocks:
                if current:
                    parts.append(current)
                current = ""
            current += char
            blocks.append(BLOCKS_CHARS[char])
            continue

        # Handle spaces outside blocks
        if not blocks and char == " ":
            if current:
                parts.append(current)
            current = ""
            continue

        current += char

    # Add remaining content
    if current:
        parts.append(current)

    return parts


def format_usage(usage_text):
    """
    Format usage text to fit within specified line length.
    Preserves block structures ([] and <>) when wrapping lines.
    """
    MAX_LENGTH = 80
    if not usage_text or len(usage_text) < MAX_LENGTH:
        return usage_text

    parts = split_respect_blocks(usage_text)

    indent = 4
    lines = []
    current_line = ""
    curlen = 0

    while parts:
        current_part = parts.pop(0)

        # Determine if part requires line wrap
        len_if_add = curlen + len(current_part) + 1
        bump_to_next_line = len_if_add > MAX_LENGTH or len(current_part) >= MAX_LENGTH

        # Special handling for options with parameters
        if not bump_to_next_line and parts and parts[0]:
            bump_to_next_line = (
                current_part.startswith("-")  # Is an option
                and parts[0][0] in ["[", "<"]  # Next part is a parameter block
                and (len_if_add + len(parts[0]) + 1)
                > MAX_LENGTH  # Won't fit current line
                and (len(current_part) + len(parts[0]) + 1)
                < MAX_LENGTH  # Will fit next line
            )

        # Start new line if needed
        if bump_to_next_line:
            if current_line:
                lines.append(current_line.rstrip())
            current_line = " " * indent

        # Add part to current line
        current_line += current_part + " "
        curlen = len(current_line)

    # Add final line
    if current_line:
        lines.append(current_line.rstrip())

    return "\n".join(lines)


def setup(app):
    """Register the directive with Sphinx."""
    app.add_directive("omnicli", OmniCLIDirective)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
