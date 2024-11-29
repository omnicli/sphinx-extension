import pytest
from docutils import nodes
from sphinx.testing.util import SphinxTestApp
import json
from unittest.mock import patch, Mock
import subprocess

from omnicli_sphinx.plugin import (
    OmniCLIDirective,
    split_respect_blocks,
    format_usage,
)


@pytest.fixture
def app():
    return SphinxTestApp()


def create_mock_output(
    name=None, usage=None, help=None, arguments=None, options=None, subcommands=None
):
    data = {}
    if name:
        data["name"] = name
    if usage:
        data["usage"] = usage
    if help:
        data["help"] = help
    if arguments:
        data["arguments"] = arguments
    if options:
        data["options"] = options
    if subcommands:
        data["subcommands"] = subcommands
    return json.dumps(data)


def test_basic_command():
    with patch("subprocess.check_output") as mock_output:
        mock_output.return_value = create_mock_output(
            usage="omni test",
            help="Test command help",
        )

        directive = OmniCLIDirective(
            name="omnicli",
            arguments=[],
            options={},
            content=[],
            lineno=0,
            content_offset=0,
            block_text="",
            state=Mock(),
            state_machine=Mock(),
        )

        result = directive.run()
        assert isinstance(result[0], nodes.section)
        assert len(result[0].children) == 3  # usage block and help paragraph


def test_title_with_name():
    with patch("subprocess.check_output") as mock_output:
        mock_output.return_value = create_mock_output(
            name="test",
            usage="omni test",
            help="Test command help",
        )

        directive = OmniCLIDirective(
            name="omnicli",
            arguments=[],
            options={},
            content=[],
            lineno=0,
            content_offset=0,
            block_text="",
            state=Mock(),
            state_machine=Mock(),
        )

        result = directive.run()
        title = result[0].children[0]
        assert isinstance(title, nodes.title)
        assert title.astext() == "omni test"


def test_title_without_name():
    with patch("subprocess.check_output") as mock_output:
        mock_output.return_value = create_mock_output(
            usage="omni test",
            help="Test command help",
        )

        directive = OmniCLIDirective(
            name="omnicli",
            arguments=[],
            options={},
            content=[],
            lineno=0,
            content_offset=0,
            block_text="",
            state=Mock(),
            state_machine=Mock(),
        )

        result = directive.run()
        title = result[0].children[0]
        assert isinstance(title, nodes.title)
        assert title.astext() == "omni"


def test_title_without_name_but_arguments():
    with patch("subprocess.check_output") as mock_output:
        mock_output.return_value = create_mock_output(
            usage="omni test",
            help="Test command help",
        )

        directive = OmniCLIDirective(
            name="omnicli",
            arguments=["testarg"],
            options={},
            content=[],
            lineno=0,
            content_offset=0,
            block_text="",
            state=Mock(),
            state_machine=Mock(),
        )

        result = directive.run()
        title = result[0].children[0]
        assert not isinstance(title, nodes.title)


def test_command_with_arguments():
    with patch("subprocess.check_output") as mock_output:
        mock_output.return_value = create_mock_output(
            arguments=[
                {"name": "arg1", "desc": "First argument"},
                {"name": "arg2", "desc": "Second argument"},
            ]
        )

        directive = OmniCLIDirective(
            name="omnicli",
            arguments=[],
            options={},
            content=[],
            lineno=0,
            content_offset=0,
            block_text="",
            state=Mock(),
            state_machine=Mock(),
        )

        result = directive.run()
        args_section = result[0].children[1]
        assert isinstance(args_section, nodes.section)
        assert len(args_section.children[1]) == 2  # Two arguments


def test_command_with_options():
    with patch("subprocess.check_output") as mock_output:
        mock_output.return_value = create_mock_output(
            options=[
                {"name": "--verbose", "desc": "Increase verbosity"},
                {"name": "--quiet", "desc": "Decrease verbosity"},
            ]
        )

        directive = OmniCLIDirective(
            name="omnicli",
            arguments=[],
            options={},
            content=[],
            lineno=0,
            content_offset=0,
            block_text="",
            state=Mock(),
            state_machine=Mock(),
        )

        result = directive.run()
        opts_section = result[0].children[1]
        assert isinstance(opts_section, nodes.section)
        assert len(opts_section.children[1]) == 2  # Two options


def test_command_with_subcommands():
    with patch("subprocess.check_output") as mock_output:
        mock_output.return_value = create_mock_output(
            subcommands=[
                {
                    "name": "cmd1, c1",
                    "desc": "First command",
                    "category": ["Category1"],
                },
                {"name": "cmd2", "desc": "Second command", "category": ["Category1"]},
            ]
        )

        directive = OmniCLIDirective(
            name="omnicli",
            arguments=[],
            options={},
            content=[],
            lineno=0,
            content_offset=0,
            block_text="",
            state=Mock(),
            state_machine=Mock(),
        )

        result = directive.run()
        subcmds_section = result[0].children[1]
        assert isinstance(subcmds_section, nodes.section)
        assert (
            len(subcmds_section.children) == 3
        )  # Title, subtitle, and definition list


def test_category_parsing():
    with patch("subprocess.check_output") as mock_output:
        mock_output.return_value = create_mock_output(
            subcommands=[
                {
                    "name": "cmd1, c1",
                    "desc": "First command",
                    "category": ["Part1", "Part2", "Part3"],
                },
            ]
        )

        directive = OmniCLIDirective(
            name="omnicli",
            arguments=[],
            options={},
            content=[],
            lineno=0,
            content_offset=0,
            block_text="",
            state=Mock(),
            state_machine=Mock(),
        )

        result = directive.run()
        subcmds_section = result[0].children[1]
        assert isinstance(subcmds_section, nodes.section)
        assert (
            len(subcmds_section.children) == 3
        )  # Title, subtitle, and definition list

        # Go to the subtitle
        subtitle = subcmds_section.children[1]
        assert isinstance(subtitle, nodes.subtitle)

        # Check the text of the subtitle
        assert subtitle.astext() == "Part3 ← Part2 ← Part1"


def test_split_respect_blocks():
    test_cases = [
        ("simple text", ["simple", "text"]),
        ("cmd [option]", ["cmd", "[option]"]),
        ("cmd <arg> [opt]", ["cmd", "<arg>", "[opt]"]),
        ("cmd [nested [block]]", ["cmd", "[nested [block]]"]),
    ]

    for input_text, expected in test_cases:
        result = split_respect_blocks(input_text)
        assert result == expected


def test_format_usage():
    test_cases = [
        (
            "omni command --option [value] <required>",
            "omni command --option [value] <required>",
        ),
        (
            "omni very-long-command --with-very-long-option [optional-value] <required-value>",
            "omni very-long-command --with-very-long-option [optional-value]\n    <required-value>",
        ),
    ]

    for input_text, expected in test_cases:
        result = format_usage(input_text)
        assert result == expected


def test_subprocess_error():
    with patch("subprocess.check_output") as mock_output:
        mock_output.side_effect = subprocess.CalledProcessError(1, "cmd")

        directive = OmniCLIDirective(
            name="omnicli",
            arguments=[],
            options={},
            content=[],
            lineno=0,
            content_offset=0,
            block_text="",
            state=Mock(),
            state_machine=Mock(),
        )

        with pytest.raises(subprocess.CalledProcessError):
            directive.run()
