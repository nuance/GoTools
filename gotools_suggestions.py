import sublime
import sublime_plugin
import json

from .gotools_util import Buffers
from .gotools_util import GoBuffers
from .gotools_util import Logger
from .gotools_util import ToolRunner
from .gotools_settings import GoToolsSettings

def _lex_func_type(typ):
  """Convert a function type into list of arguments and return value names"""
  args = []
  returns = []

  current = args
  parens_depth = 0

  val = ''
  for char in typ[4:].strip():
    if char == '(':
      if parens_depth != 0:
        val += '('

      parens_depth += 1
    elif char == ')':
      parens_depth -= 1
      if parens_depth != 0:
        val += ')'

      if parens_depth == 0:
        current.append(val.strip())
        val = ''
        current = returns
    elif char == ',':
      if parens_depth == 1:
        current.append(val.strip())
        val = ''
    else:
      val += char

  return args, returns

class GotoolsSuggestions(sublime_plugin.EventListener):
  CLASS_SYMBOLS = {
    "func": "ƒ",
    "var": "ν",
    "type": "ʈ",
    "package": "ρ"
  }

  def on_query_completions(self, view, prefix, locations):
    if not GoBuffers.is_go_source(view) or not GoToolsSettings.get().autocomplete:
      return

    suggestions_json_str, stderr, rc = ToolRunner.run("gocode", ["-f=json", "autocomplete", 
      str(Buffers.offset_at_cursor(view)[0])], stdin=Buffers.buffer_text(view))

    suggestions_json = json.loads(suggestions_json_str)

    Logger.log("DEBUG: gocode output: " + suggestions_json_str)

    if rc != 0:
      Logger.status("no completions found: " + str(e))
      return []
    
    if len(suggestions_json) > 0:
      return ([GotoolsSuggestions.build_suggestion(j) for j in suggestions_json[1]], sublime.INHIBIT_WORD_COMPLETIONS)
    else:
      return []

  @staticmethod
  def build_suggestion(json):
    completion = json["name"]
    if json["class"] == 'func':
      args, _ = _lex_func_type(json["type"])
      snippets = ["${{{0}:{1}}}".format(n + 1, arg.split(' ', 1)[0]) for n, arg in enumerate(args)]
      completion += '(' + ', '.join(snippets) + ')'

    label = '{0: <30.30} {1: <40.40} {2}'.format(
      json["name"],
      json["type"],
      GotoolsSuggestions.CLASS_SYMBOLS.get(json["class"], "?"))
    return (label, completion)
