import sublime
import sublime_plugin
import re
import os

from .gotools_util import Buffers
from .gotools_util import GoBuffers
from .gotools_util import Logger
from .gotools_util import ToolRunner
from .gotools_settings import GoToolsSettings


class GotoolsLintOnSave(sublime_plugin.EventListener):
    def on_post_save_async(self, view):
        if not GoBuffers.is_go_source(view):
            return
        if not GoToolsSettings.get().lint_on_save:
            return
        view.run_command('gotools_lint')

LINTERS = [
    # ('go', ['install', '-v'], "^(.*):(\d+):(\d+):(.*)$", lambda ll: ll['rc'] == 1, lambda stderr, stdout: stderr),
    ('go', ['vet'], "^(.*):(\d+):(.*)$", lambda ll: ll['rc'] == 1, lambda stderr, stdout: stderr),
    ('golint', [], "^(.*):(\d+):(\d+):(.*)$", lambda ll: len(ll['stdout']) > 0, lambda stderr, stdout: stdout),
]


class GotoolsLint(sublime_plugin.TextCommand):
    def is_enabled(self):
        return GoBuffers.is_go_source(self.view)

    def run(self, edit):
        for l in LINTERS:
            self._run_cmd_or_fail(*l)

    def _run_cmd_or_fail(self, cmd, args, file_regex, failure_test, failures):
        path = os.path.dirname(self.view.file_name())
        stdout, stderr, rc = ToolRunner.run(cmd, args, cwd=path)

        # Clear previous syntax error marks
        self.view.erase_regions("GotoolsLint")

        if failure_test(locals()):
            # Show syntax errors and bail
            self.show_syntax_errors(failures(stderr, stdout), file_regex)
            return True

        # Everything's good, hide the syntax error panel
        self.view.window().run_command("hide_panel", {"panel": "output.gotools_lint_errors"})

    def show_syntax_errors(self, stderr, file_regex):
        """Display an output panel containing the syntax errors, and set gutter marks for each error."""
        output_view = self.view.window().create_output_panel('gotools_lint_errors')
        output_view.set_scratch(True)
        output_view.settings().set("result_file_regex", file_regex)
        output_view.run_command("select_all")
        output_view.run_command("right_delete")

        syntax_output = stderr.replace(os.path.basename(self.view.file_name()), self.view.file_name())
        output_view.run_command('append', {'characters': syntax_output})
        self.view.window().run_command("show_panel", {"panel": "output.gotools_lint_errors"})

        marks = []
        for error in stderr.splitlines():
            match = re.match(file_regex, error)
            if not match or not match.group(2):
                Logger.log("skipping unrecognizable error:\n" + error + "\nmatch:" + str(match))
                continue

            row = int(match.group(2))
            pt = self.view.text_point(row - 1, 0)
            Logger.log("adding mark at row " + str(row))
            marks.append(sublime.Region(pt))

        if len(marks) > 0:
            self.view.add_regions("GotoolsLint", marks, "source.go", "dot", sublime.DRAW_STIPPLED_UNDERLINE | sublime.PERSISTENT)
