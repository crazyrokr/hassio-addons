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

TAR_READER = TarReader()
logger = logging.getLogger(__name__)


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
    server = server_class(('', port), handler_class)
    print(f"Server started on http://localhost:{port}")
    server.serve_forever()

if __name__ == "__main__":
    run()
