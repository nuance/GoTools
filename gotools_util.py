import sublime
import os
import re
import platform
import subprocess
import time

import golangconfig


class Buffers():
  @staticmethod
  def offset_at_row_col(view, row, col):
    point = view.text_point(row, col)
    select_region = sublime.Region(0, point)
    string_region = view.substr(select_region)
    buffer_region = bytearray(string_region, encoding="utf8")
    offset = len(buffer_region)
    return offset

  @staticmethod
  def buffer_text(view):
    file_text = sublime.Region(0, view.size())
    return view.substr(file_text).encode('utf-8')

  @staticmethod
  def offset_at_cursor(view):
    begin_row, begin_col = view.rowcol(view.sel()[0].begin())
    end_row, end_col = view.rowcol(view.sel()[0].end())

    return (Buffers.offset_at_row_col(view, begin_row, begin_col), Buffers.offset_at_row_col(view, end_row, end_col))

  @staticmethod
  def symbol_offset_at_cursor(view):
    start_position = view.rowcol(view.word(view.sel()[0]).begin())
    end_position = view.rowcol(view.word(view.sel()[0]).end())

    return Buffers.offset_at_row_col(view, *start_position), Buffers.offset_at_row_col(view, *end_position)

  @staticmethod
  def location_at_cursor(view):
    row, col = view.rowcol(view.sel()[0].begin())
    offsets = Buffers.offset_at_cursor(view)
    return (view.file_name(), row, col, offsets[0], offsets[1])

  @staticmethod
  def location_for_event(view, event):
    pt = view.window_to_text((event["x"], event["y"]))
    row, col = view.rowcol(pt)
    offset = Buffers.offset_at_row_col(view, row, col)
    return (view.file_name(), row, col, offset)

class GoBuffers():
  @staticmethod
  def func_name_at_cursor(view):
    func_regions = view.find_by_selector('meta.function')

    func_name = ""
    for r in func_regions:
      if r.contains(Buffers.offset_at_cursor(view)[0]):
        lines = view.substr(r).splitlines()
        match = re.match('func.*(Test.+)\(', lines[0])
        if match and match.group(1):
          func_name = match.group(1)
          break

    return func_name

  @staticmethod
  def is_go_source(view):
    return view.score_selector(0, 'source.go') != 0

class Logger():
  @staticmethod
  def log(msg):
    pass
    # if golangconfig.setting_value('debug_enabled')[0]:
    #   print("GoTools: DEBUG: {0}".format(msg))

  @staticmethod
  def error(msg):
    print("GoTools: ERROR: {0}".format(msg))

  @staticmethod
  def status(msg):
    sublime.status_message("GoTools: " + msg)

class ToolRunner():
  @staticmethod
  def prepare(view, tool):
    return golangconfig.subprocess_info(tool, ['GOPATH', 'PATH'], view=view)

  @staticmethod
  def run_prepared(prepared, args=[], stdin=None, timeout=5, cwd=None):
    toolpath, env = prepared
    return ToolRunner._run(toolpath, env, args, stdin, timeout, cwd)

  @staticmethod
  def run(view, tool, args=[], stdin=None, timeout=5, cwd=None):
    toolpath, env = golangconfig.subprocess_info(tool, ['GOPATH', 'PATH'], view=view)
    return ToolRunner._run(toolpath, env, args, stdin, timeout, cwd)

  @staticmethod
  def _run(toolpath, env, args=[], stdin=None, timeout=5, cwd=None):
    cmd = [toolpath] + args
    try:
      Logger.log("spawning process...")
      Logger.log("\tcommand:     " + " ".join(cmd))
      Logger.log("\tenvironment: " + str(env))

      # Hide popups on Windows
      si = None
      if platform.system() == "Windows":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

      start = time.time()
      p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, startupinfo=si, cwd=cwd)
      stdout, stderr = p.communicate(input=stdin, timeout=timeout)
      p.wait(timeout=timeout)
      elapsed = round(time.time() - start)
      Logger.log("process returned ({0}) in {1} seconds".format(str(p.returncode), str(elapsed)))
      stderr = stderr.decode("utf-8")
      if len(stderr) > 0:
        Logger.log("stderr:\n{0}".format(stderr))
      x = stdout.decode("utf-8"), stderr, p.returncode
      return x
    except subprocess.CalledProcessError as e:
      raise
