import sublime
import sublime_plugin
import json

from .gotools_util import Buffers
from .gotools_util import GoBuffers
from .gotools_util import Logger
from .gotools_util import ToolRunner
from .gotools_settings import GoToolsSettings


class GotoolsShowTypeCommand(sublime_plugin.EventListener):
  def __init__(self):
    self.offset = None

  def is_enabled(self):
    return GoBuffers.is_go_source(self.view)

  def on_selection_modified_async(self, view):
    offset = Buffers.symbol_offset_at_cursor(view)
    if offset == self.offset:
      return
    self.offset = offset

    suggestions_json_str, stderr, rc = ToolRunner.run("gocode", ["-f=json", "autocomplete", 
      str(offset)], stdin=Buffers.buffer_text(view))

    parts = json.loads(suggestions_json_str)
    typ = ''
    if parts and parts[1]:
      name = view.substr(view.word(view.sel()[0]))
      exact = [p for p in parts[1] if p['name'] == name]
      if exact:
        typ = '{0}: {1}'.format(name, exact[0]["type"])

    view.set_status("Gotools.show_type", typ)
