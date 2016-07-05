import sublime
import sublime_plugin
import os
import re
import time

from .gotools_util import Logger
from .gotools_util import ToolRunner

LINTERS = [
    # ('go', ['install', '-v'], "^(.*\.go):(\d+):(\d+):(.*)$", lambda ll: ll['rc'] == 1, lambda stderr, stdout: stderr),
    ('go', ['vet'], "^(.*\.go):(\d+):(.*)$", lambda ll: ll['rc'] == 1, lambda stderr, stdout: stderr),
    ('golint', [], "^(.*\.go):(\d+):(\d+):(.*)$", lambda ll: len(ll['stdout']) > 0, lambda stderr, stdout: stdout),
]


class GotoolsLint(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings):
        return settings.get('syntax') == 'Packages/GoTools/GoTools.tmLanguage'

    def __init__(self, view):
        self.view = view
        self.phantom_set = sublime.PhantomSet(view)

        self.timeout_scheduled = False
        self.last_modified = 0

        self.prepared = {l[0]: ToolRunner.prepare(view, l[0]) for l in LINTERS}

    def on_modified(self):
        self.last_modified = time.time()
        if self.timeout_scheduled:
            return

        self.timeout_scheduled = True
        sublime.set_timeout_async(self.lint, 500)

    def lint(self):
        now = time.time()
        if now - self.last_modified < 0.5:
            sublime.set_timeout_async(self.lint, 500)
            return

        print('linting ' + self.view.file_name())

        phantoms = []
        for l in LINTERS:
            phantoms.extend(self._run_cmd_or_fail(*l, **{'include_other_files': False}))

        self.phantom_set.update(phantoms)
        self.timeout_scheduled = False

    def _run_cmd_or_fail(self, cmd, args, file_regex, failure_test, failures, include_other_files):
        path = os.path.dirname(self.view.file_name())
        stdout, stderr, rc = ToolRunner.run_prepared(self.prepared[cmd], args, cwd=path)

        if failure_test(locals()):
            # Show syntax errors and bail
            return self.show_syntax_errors('## {0} ##'.format(' '.join([cmd] + args)),
                                           failures(stderr, stdout),
                                           file_regex,
                                           include_other_files)
        return []

    def show_syntax_errors(self, header, stderr, file_regex, include_other_files):
        """Display an output panel containing the syntax errors, and set gutter marks for each error."""
        file_name = os.path.basename(self.view.file_name())
        dir_name = os.path.dirname(self.view.file_name())

        lines = []
        for line in stderr.split('\n'):
            m = re.search(file_regex, line)
            if m:
                line = os.path.join(dir_name, line)

                if include_other_files and file_name not in line:
                    continue
            lines.append(line)

        if not any(lines):
            return []

        phantoms = []
        for error in stderr.splitlines():
            if file_name not in error:
                continue

            match = re.match(file_regex, error)
            if not match or not match.group(2):
                Logger.log("skipping unrecognizable error:\n" + error + "\nmatch:" + str(match))
                continue

            row = int(match.group(2)) - 1
            column = 0
            if len(match.groups()) == 4:
                column = int(match.group(3)) - 1

            error = '<div class="warning">^ {}</div>'.format(match.groups()[-1].strip())

            pt = self.view.text_point(row, column)
            phantoms.append(sublime.Phantom(sublime.Region(pt), error, sublime.LAYOUT_BELOW))

        return phantoms
