import sublime
import sublime_plugin
import os
import json

from .gotools_util import Buffers
from .gotools_util import GoBuffers
from .gotools_util import Logger
from .gotools_util import ToolRunner

import golangconfig

class GotoolsGotoDef(sublime_plugin.TextCommand):
  def is_enabled(self):
    return GoBuffers.is_go_source(self.view)

  # Capture mouse events so users can click on a definition.
  def want_event(self):
    return True

  def run(self, edit, event=None):
    # Find and store the current filename and byte offset at the
    # cursor or mouse event location.
    if event:
      filename, row, col, offset = Buffers.location_for_event(self.view, event)
    else:
      filename, row, col, offset, offset_end = Buffers.location_at_cursor(self.view)

    backend = golangconfig.setting_value('goto_def_backend')[0] or "godef"
    try:
      if backend == "oracle":
        file, row, col = self.get_oracle_location(filename, offset)
      elif backend == "godef":
        file, row, col = self.get_godef_location(filename, offset)
      else:
        Logger.log("Invalid godef backend '" + backend + "' (supported: godef, oracle)")
        Logger.status("Invalid godef configuration; see console log for details")
        return
    except Exception as e:
     Logger.status(str(e))
     return
    
    if not os.path.isfile(file):
      Logger.log("WARN: file indicated by godef not found: " + file)
      Logger.status("godef failed: Please enable debugging and check console log")
      return
    
    Logger.log("opening definition at " + file + ":" + str(row) + ":" + str(col))
    w = self.view.window()
    new_view = w.open_file(file + ':' + str(row) + ':' + str(col), sublime.ENCODED_POSITION)
    group, index = w.get_view_index(new_view)
    if group != -1:
        w.focus_group(group)

  def get_oracle_location(self, filename, offset):
    args = ["-pos="+filename+":#"+str(offset), "-format=json", "definition"]

    # Build up a package scope contaning all packages the user might have
    # configured.
    # TODO: put into a utility
    package_scope = []
    for p in golangconfig.setting_value('build_packages')[0]:
      package_scope.append(os.path.join(golangconfig.setting_value('project_package')[0], p))
    for p in golangconfig.setting_value('test_packages')[0]:
      package_scope.append(os.path.join(golangconfig.setting_value('project_package')[0], p))
    for p in golangconfig.setting_value('tagged_test_packages')[0]:
      package_scope.append(os.path.join(golangconfig.setting_value('project_package')[0], p))

    if len(package_scope) > 0:
      args = args + package_scope

    location, err, rc = ToolRunner.run(self.view, "oracle", args)
    if rc != 0:
      raise Exception("no definition found")

    Logger.log("oracle output:\n" + location.rstrip())

    # cut anything prior to the first path separator
    location = json.loads(location.rstrip())['definition']['objpos'].rsplit(":", 2)

    if len(location) != 3:
      raise Exception("no definition found")

    file = location[0]
    row = int(location[1])
    col = int(location[2])

    return [file, row, col]

  def get_godef_location(self, filename, offset):
    location, err, rc = ToolRunner.run(self.view, "godef", ["-f", filename, "-o", str(offset)])
    if rc != 0:
      raise Exception("no definition found")

    Logger.log("godef output:\n" + location.rstrip())

    # godef is sometimes returning this junk as part of the output,
    # so just cut anything prior to the first path separator
    location = location.rstrip().rsplit(":", 2)

    if len(location) != 3:
      raise Exception("no definition found")

    file = location[0]
    row = int(location[1])
    col = int(location[2])

    return [file, row, col]
