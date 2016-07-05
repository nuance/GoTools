import sublime
import sublime_plugin
import json

from .gotools_util import Buffers
from .gotools_util import ToolRunner


class GotoolsShowTypeCommand(sublime_plugin.ViewEventListener):
  @classmethod
  def is_applicable(cls, settings):
    return settings.get('syntax') == 'Packages/GoTools/GoTools.tmLanguage'

  def __init__(self, view):
    self.offset = None
    self.view = view
    self.phantom_set = sublime.PhantomSet(view)

    self.gocode = ToolRunner.prepare(view, 'gocode')

  def on_selection_modified_async(self):
    start, end = Buffers.symbol_offset_at_cursor(self.view)
    if end == self.offset:
      return
    self.offset = end

    suggestions_json_str, stderr, rc = ToolRunner.run_prepared(self.gocode, ["-f=json", "autocomplete", 
      str(end)], stdin=Buffers.buffer_text(self.view))

    parts = json.loads(suggestions_json_str)
    typ = ''
    if parts and parts[1]:
      name = self.view.substr(self.view.word(self.view.sel()[0]))
      exact = [p for p in parts[1] if p['name'] == name]
      if exact:
        typ = exact[0]["type"]

    phantoms = [sublime.Phantom(sublime.Region(start, start), typ, sublime.LAYOUT_BELOW)] if typ else []
    self.phantom_set.update(phantoms)
