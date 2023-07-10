import jinja2
import json
import pytest
from mkdocs_nixos_options.plugin import NixOsOptionsPlugin


def test_plugin_disable():
    plugin = NixOsOptionsPlugin()
    plugin.config["enable"] = False
    plugin.config["nix_bin"] = "nix"
    plugin.config["nix_command_extra_args"] = ""
    plugin.config["template"] = "default"
    assert (
        plugin.on_page_markdown("::nixos-options::module_path::", None, None, None)
        == "::nixos-options::module_path::"
    )


def test_eval_expression():
    plugin = NixOsOptionsPlugin()
    plugin.config["enable"] = False
    plugin.config["nix_bin"] = "nix"
    plugin.config["nix_command_extra_args"] = ""
    plugin.config["template"] = "default"
    expression = plugin.eval_expression("example_module_path")
    assert "optionsPath = example_module_path" in expression


def test_call_nix_bin(mocker):
    mock = mocker.patch("subprocess.run", autospec=True)
    mock.return_value.returncode = 0
    mock.return_value.stdout = b'{"key": {"type": "str", "description": "example description", "default": "example default"}}'
    plugin = NixOsOptionsPlugin()
    plugin.config["enable"] = True
    plugin.config["nix_bin"] = "nix"
    plugin.config["nix_command_extra_args"] = ""
    plugin.config["template"] = "default"
    result = plugin.call_nix_bin("example_module_path")
    assert result == {
        "key": {
            "type": "str",
            "description": "example description",
            "default": "example default",
        }
    }


def test_call_nix_bin_command_error(mocker):
    mock = mocker.patch("subprocess.run", autospec=True)
    mock.return_value.returncode = 1
    mock.return_value.stdout = b""
    plugin = NixOsOptionsPlugin()
    plugin.config["enable"] = True
    plugin.config["nix_bin"] = "nix"
    plugin.config["nix_command_extra_args"] = ""
    plugin.config["template"] = "default"
    with pytest.raises(Exception, match="Failed to run nix command: "):
        plugin.call_nix_bin("example_module_path")


def test_call_nix_bin_json_decode_error(mocker):
    mock = mocker.patch("subprocess.run", autospec=True)
    mock.return_value.stdout = b"not json"
    mock.return_value.returncode = 0
    plugin = NixOsOptionsPlugin()
    plugin.config["enable"] = True
    plugin.config["nix_bin"] = "nix"
    plugin.config["nix_command_extra_args"] = ""
    with pytest.raises(json.JSONDecodeError):
        plugin.call_nix_bin("example_module_path")


def test_on_page_markdown_no_match():
    plugin = NixOsOptionsPlugin()
    plugin.config["enable"] = True
    plugin.config["nix_bin"] = "nix"
    plugin.config["nix_command_extra_args"] = ""
    plugin.config["template"] = "default"
    markdown = "no match here"
    result = plugin.on_page_markdown(markdown, None, None, None)
    assert result == markdown


def test_on_page_markdown_with_match(mocker):
    mock_run = mocker.patch("subprocess.run", autospec=True)
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = b'{"key": {"type": "str", "description": "example description", "default": "example default"}}'
    plugin = NixOsOptionsPlugin()
    plugin.config["enable"] = True
    plugin.config["nix_bin"] = "nix"
    plugin.config["nix_command_extra_args"] = ""
    plugin.config["template"] = "default"
    markdown = "::nixos-options::module_path::"
    result = plugin.on_page_markdown(markdown, None, None, None)
    assert "## `key`" in result
    assert "| str | example description | example default |" in result


def test_on_page_markdown_with_invalid_template(mocker):
    mock_run = mocker.patch("subprocess.run", autospec=True)
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = b'{"key": {"type": "str", "description": "example description", "default": "example default"}}'
    plugin = NixOsOptionsPlugin()
    plugin.config["enable"] = True
    plugin.config["nix_bin"] = "nix"
    plugin.config["nix_command_extra_args"] = ""
    plugin.config["template"] = "/invented/path"
    markdown = "::nixos-options::module_path::"
    with pytest.raises(jinja2.exceptions.TemplateNotFound, match="/invented/path"):
        plugin.on_page_markdown(markdown, None, None, None)


def test_on_page_markdown_with_unknown_type(mocker):
    mock_run = mocker.patch("subprocess.run", autospec=True)
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = b'{"key": {"type": "unknown", "description": "example description", "default": "example default"}}'
    plugin = NixOsOptionsPlugin()
    plugin.config["enable"] = True
    plugin.config["nix_bin"] = "nix"
    plugin.config["nix_command_extra_args"] = ""
    plugin.config["template"] = "default"
    markdown = "::nixos-options::module_path::"

    result = plugin.on_page_markdown(markdown, None, None, None)
    assert "## `key`" not in result
