import json
import logging
import re
import subprocess
import textwrap
import os
from jinja2 import Environment, FileSystemLoader
from jinja2.loaders import DictLoader
from jinja2.exceptions import TemplateSyntaxError

from mkdocs.plugins import BasePlugin
from mkdocs.config import config_options


class NixOsOptionsPlugin(BasePlugin):
    """MkDocs plugin to easily render NixOS module options."""

    NIX_OPTIONS_MARKER = "nixos-options"

    config_scheme = (
        ("enable", config_options.Type(bool, default=True)),
        ("nix_bin", config_options.Type(str, default="nix")),
        ("nix_command_extra_args", config_options.Type(str, default="")),
        ("template", config_options.Type(str, default="default")),
    )

    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("mkdocs.plugins.nixos-options")
        self.default_template = textwrap.dedent(
            """
            ## `{{ key }}`
            
            **Snippet**
            
            ```nix
            {{ key }}
            ```
            
            **Parameter**
            
            | Type       | Description       | Default       |
            | ---------- | ----------------- | ------------- |
            | {{ type }} | {{ description }} | {{ default }} |
            
        """
        )

        template_file = self.config.get("template", "default")
        if template_file != "default" and os.path.isfile(template_file):
            directory, _ = os.path.split(template_file)
            loader = FileSystemLoader(directory)
        else:
            loader = DictLoader({"default": self.default_template})

        self.env = Environment(loader=loader)

    def on_page_markdown(self, markdown, page, config, files):
        if (
            self.config["enable"]
            and markdown
            and f"::{self.NIX_OPTIONS_MARKER}::" in markdown
        ):
            pattern = f"::{self.NIX_OPTIONS_MARKER}::(?P<module_path>.*?)::"
            for match in re.finditer(pattern, markdown):
                module_path = match.group("module_path")
                data = self.call_nix_bin(module_path)
                markdown_string = ""
                try:
                    template = self.env.get_template(self.config["template"])
                except TemplateSyntaxError as e:
                    self.log.error(
                        f"Failed to load the template due to syntax error: {str(e)}"
                    )
                    raise

                for key, value in data.items():
                    self.log.debug(f"Processing key {key} with value {value}")

                    if value.get("type") != "unknown":
                        type_value = value.get("type", "")
                        description = value.get("description", "")
                        default = value.get("default", "")
                        if isinstance(default, dict):
                            default = default.get("text", "")
                        try:
                            markdown_string += template.render(
                                key=key,
                                type=type_value,
                                description=description,
                                default=default,
                            )
                        except Exception as e:
                            self.log.error(f"Failed to render the template: {str(e)}")
                            raise

                markdown = markdown.replace(
                    f"::{self.NIX_OPTIONS_MARKER}::{module_path}::",
                    markdown_string,
                )

        return markdown

    def eval_expression(self, module_path):
        nix_expression = f"""
        (
          {{
            pkgs ? import <nixpkgs> {{}},
            lib ? pkgs.lib,
            optionsPath,
            transformOptions ? lib.id,
          }}:
          with lib;
          with builtins; let
            options = evalModules {{modules = [optionsPath];}};
            rawOpts = optionAttrSetToDocList options;
            transformedOpts = map transformOptions rawOpts;
            filteredOpts = filter (opt: opt.visible && !opt.internal) transformedOpts;
            optionsList = flip map filteredOpts (opt: opt);
            optionsNix = listToAttrs (map (o: {{
                name = o.name;
                value = removeAttrs o ["name" "visible" "internal"];
              }})
              optionsList);
          in
            optionsNix
        ) {{optionsPath = {module_path};}}
        """
        return textwrap.dedent(nix_expression)

    def call_nix_bin(self, module_path):
        command = [
            self.config["nix_bin"],
            "eval",
            "--impure",
            "--json",
            "--expr",
            self.eval_expression(module_path),
            self.config["nix_command_extra_args"],
        ] + ["--extra-experimental-features", "flakes nix-command"]
        self.log.debug(f"Running command: {' '.join(command)}")
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
            )
        except Exception as e:
            self.log.error(
                f"Failed to run command: {' '.join(command)}. Error: {str(e)}"
            )
            raise

        if result.returncode != 0:
            self.log.error(f"Failed to run nix command: {result.stderr}")
            raise Exception(
                f"Failed to run nix command: {result.stderr}. Command: {' '.join(command)}"
            )

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            self.log.error("Failed to parse nix output as JSON")
            self.log.debug(f"Nix output that failed to parse: {result.stdout}")
            raise

        return data
