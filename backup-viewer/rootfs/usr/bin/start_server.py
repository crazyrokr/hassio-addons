#!/usr/bin/env python3
import json
import os
import logging
import shutil
import tarfile
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from tar_reader import TarReader
from string import Template
from rcssmin import cssmin
from rjsmin import jsmin

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

TAR_READER = TarReader()
logger = logging.getLogger(__name__)


class BackupDirEventHandler(FileSystemEventHandler):

    def __init__(self, tar_reader_instance):
      super().__init__()
      self.tar_reader = tar_reader_instance
      self.backup_dir = next(iter(tar_reader_instance._passwords))
      self.archive_ext = tar_reader_instance._archive_ext

    def _is_relevant_file(self, path):
      return os.path.dirname(path) == self.backup_dir and \
              path.lower().endswith(self.archive_ext)

    def on_created(self, event):
      if not event.is_directory and self._is_relevant_file(event.src_path):
        logger.info(f"File created: {event.src_path}. Invalidating cache.")
        self.tar_reader.invalidate_cache()
        self.tar_reader.read_backup_dir()

    def on_deleted(self, event):
      if not event.is_directory and self._is_relevant_file(event.src_path):
        logger.info(f"File deleted: {event.src_path}. Invalidating cache.")
        self.tar_reader.invalidate_cache()
        self.tar_reader.read_backup_dir()

    def on_moved(self, event):
      if not event.is_directory and \
          (self._is_relevant_file(event.src_path) or \
            self._is_relevant_file(event.dest_path)):
        logger.info(f"File moved: {event.src_path} to {event.dest_path}. \
                      Invalidating cache.")
        self.tar_reader.invalidate_cache()
        self.tar_reader.read_backup_dir()

    def on_modified(self, event):
      if not event.is_directory and self._is_relevant_file(event.src_path):
        logger.info(f"File modified: {event.src_path}. Invalidating cache.")
        self.tar_reader.invalidate_cache()
        self.tar_reader.read_backup_dir()


class MyHandler(SimpleHTTPRequestHandler):

  def do_GET(self):
    parsed = urlparse(self.path)
    if parsed.path == "/":
      with open('/usr/bin/index.html', 'r') as html_file, \
           open('/usr/bin/script.js', 'r') as js_file, \
           open('/usr/bin/style.css', 'r') as css_file:
        html = html_file.read()
        js = js_file.read()
        css = css_file.read()
        js = jsmin(js)
        css = cssmin(css)
        html = Template(html).substitute(style=css, script=js)
        html_bytes = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', "text/html; charset=utf-8")
        self.send_header('Content-Length', str(len(html_bytes)))
        self.end_headers()
        self.wfile.write(html_bytes)
        self.wfile.flush()
    elif parsed.path == "/tarinfo":
      try:
        result = TAR_READER.read_backup_dir()
        file_tree = json.dumps(result, ensure_ascii=False, separators=(',', ':'))
        file_tree_bytes = file_tree.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', "application/json; charset=utf-8")
        self.send_header('Content-Length', str(len(file_tree_bytes)))
        self.end_headers()
        self.wfile.write(file_tree_bytes)
        self.wfile.flush()
      except Exception as error:
        raise RuntimeError('Collect TAR members failed.') from error
    elif parsed.path == "/download":
      try:
        query_args = parse_qs(parsed.query)
        archive = query_args['archive'][0]
        l1_member = query_args['l1'][0]
        l2_member = query_args['l2'][0] if 'l2' in query_args else None
        file_name = os.path.basename(l2_member if l2_member else l1_member)
        file_name = 'filename="{}"'.format(file_name)
        with tarfile.open(archive, 'r:*') as backup_file, \
             TAR_READER.extract(backup_file, l1_member, l2_member) as result:
          info, file = result
          self.send_response(200)
          self.send_header('Content-Type', 'application/octet-stream')
          self.send_header('Content-Disposition', 'attachment; ' + file_name)
          self.send_header('Content-Length', str(info.size))
          self.end_headers()
          shutil.copyfileobj(file, self.wfile)
      except Exception as error:
        raise RuntimeError('Download TAR member failed.') from error

def run(server_class=HTTPServer, handler_class=MyHandler, port=8099):
  backup_dir = next(iter(TAR_READER._passwords))

  event_handler = BackupDirEventHandler(TAR_READER)
  observer = Observer()
  observer.schedule(event_handler, backup_dir, recursive=False)
  observer.start()

  print(f"Server started on http://localhost:{port}")
  print(f"Watching directory for changes: {backup_dir}")
  try:
    server = server_class(('', port), handler_class)
    server.serve_forever()
  except KeyboardInterrupt:
    pass
  finally:
    observer.stop()
    observer.join()
    print("Watcher stopped.")

if __name__ == "__main__":
  try:
    print("Pre-caching backup directory structure...")
    TAR_READER.read_backup_dir()
    print("Pre-caching complete.")
  except Exception as e:
    logger.error(f"Error during pre-caching: {e}")
  run()
