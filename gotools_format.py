import sublime
import sublime_plugin
import os
import golangconfig
import re

from .gotools_util import Buffers
from .gotools_util import GoBuffers
from .gotools_util import Logger
from .gotools_util import ToolRunner

class GotoolsFormatOnSave(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        if not GoBuffers.is_go_source(view):
            return
        if not golangconfig.setting_value("format_on_save")[0]:
            return
        view.run_command('gotools_format')

class GotoolsFormat(sublime_plugin.TextCommand):
    def __init__(self, view):
        super().__init__(view)
        self.phantom_set = sublime.PhantomSet(self.view)

    def is_enabled(self):
        return GoBuffers.is_go_source(self.view)

    def run(self, edit):
        command = ""
        args = []
        if golangconfig.setting_value('format_backend')[0] == "gofmt":
            command = "gofmt"
            args = ["-e", "-s"]
        elif golangconfig.setting_value('format_backend')[0] in ["goimports", "both"]:
            command = "goimports"
            args = ["-e"]

        stdout, stderr, rc = ToolRunner.run(self.view, command, args, stdin=Buffers.buffer_text(self.view))

        # Clear previous syntax error marks
        self.view.erase_regions("mark")

        if rc == 2:
            # Show syntax errors and bail
            self.show_syntax_errors(stderr)
            return

        if rc != 0:
            # Ermmm...
            Logger.log("unknown gofmt error (" + str(rc) + ") stderr:\n" + stderr)
            self.phantom_set.update([])
            return

        if golangconfig.setting_value('format_backend')[0] == "both":
            command = "gofmt"
            args = ["-e", "-s"]
            stdout, stderr, rc = ToolRunner.run(self.view, command, args, stdin=stdout.encode('utf-8'))

        # Clear previous syntax error marks
        self.view.erase_regions("mark")

        if rc == 2:
            # Show syntax errors and bail
            self.show_syntax_errors(stderr)
            return

        if rc != 0:
            # Ermmm...
            Logger.log("unknown gofmt error (" + str(rc) + ") stderr:\n" + stderr)
            self.phantom_set.update([])
            return

        # Everything's good, hide the syntax error panel
        self.phantom_set.update([])

    # Display an output panel containing the syntax errors, and set gutter marks for each error.
    def show_syntax_errors(self, stderr):
        phantoms = []
        for error in stderr.splitlines():
            match = re.match("(.*):(\d+):(\d+):(.*)", error)
            if not match or not match.group(2):
                Logger.log("skipping unrecognizable error:\n" + error + "\nmatch:" + str(match))
                continue

            row = int(match.group(2)) - 1
            column = int(match.group(3)) - 1

            error = '<div class="error">^ {}</div>'.format(match.group(4).strip())

            pt = self.view.text_point(row, column)
            phantoms.append(sublime.Phantom(sublime.Region(pt), error, sublime.LAYOUT_BELOW))

        self.phantom_set.update(phantoms)
