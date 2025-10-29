import json
import os
import time
import traceback
import os.path
from aes_file import AesFile
from tarfile import TarInfo, TarFile
from typing import IO, Iterator, Tuple
from contextlib import contextmanager
from concurrent.futures import ProcessPoolExecutor, as_completed


class TarReader:

  def __init__(self):
    backup_dir = os.environ['HABV_BACKUP_FOLDER']
    password = os.environ['HABV_BACKUP_PASSWORD']
    self._passwords: dict = {}
    self._passwords[os.path.normpath(backup_dir)] = password
    self._archive_ext = ('.tar', '.tar.gz', '.tgz')
    self._cpu_count = os.cpu_count() or 4

  @contextmanager
  def extract(
    self,
    backup_file: TarFile,
    l1_member: str,
    l2_member: str=None
  ) -> Iterator[Tuple[TarInfo, IO[bytes]]]:
    gen = None
    if l2_member:
      gen = self.extract_l2(backup_file, l1_member, l2_member)
    else:
      gen = self.extract_l1(backup_file, l1_member)
    info, file = next(gen, None)
    try:
      yield info, file
    finally:
      file.close()

  def extract_l1(
    self,
    tar_file: TarFile,
    path: str
  ) -> Iterator[Tuple[TarInfo, IO[bytes]]]:
    found = None
    try:
      found = tar_file.getmember(f'./{path}')
    except KeyError:
      found = tar_file.getmember(path)
    yield found, tar_file.extractfile(found)

  def extract_l2(
    self,
    backup: TarFile,
    l1_member: str,
    l2_member: str
  ) -> Iterator[Tuple[TarInfo, IO[bytes]]]:
    with self.open_gzip(backup, l1_member) as tar_file:
      for member_info, extracted_file in self.extract_l1(tar_file, l2_member):
        yield member_info, extracted_file

  @contextmanager
  def try_decrypt(self, file: TarFile, backup_json: IO[bytes], backup_path: str):
    if self.is_encrypted(backup_json):
      password = self._passwords[os.path.dirname(backup_path)]
      file = AesFile(password, file)
    try:
      yield file
    finally:
      file.close()

  def read_tar_metadata(self, tar_file: TarFile) -> list[dict]:
    folders: list[TarInfo] = []
    zips: list[TarInfo] = []
    files: list[TarInfo] = []
    members = tar_file.getmembers()
    for member in sorted(members, key=lambda m: m.name):
      if member.name == ".":
        continue
      elif member.isdir():
        folders.append(member)
      elif member.name.endswith('.tar.gz'):
        zips.append(member)
      else:
        files.append(member)
    return [
      *self.get_fs_members(folders, 'dir'),
      *self.get_gzip_members(tar_file, zips, 'zip'),
      *self.get_fs_members(files, 'file'),
    ]

  def get_fs_members(
    self,
    members: list[TarInfo],
    file_type: str
  ) -> list[dict]:
    results = []
    for member in members:
      fs_member = FsMember(member.name, file_type, None, member.size, member.mtime)
      results.append(fs_member.__dict__)
    return results

  @contextmanager
  def open_gzip(self, outer_tar: TarFile, gzip_name: str):
    with outer_tar.extractfile(gzip_name) as fileobj, \
         outer_tar.extractfile('./backup.json') as backup_json, \
         self.try_decrypt(fileobj, backup_json, outer_tar.name) as decrypted, \
         TarFile.open(name=gzip_name, fileobj=decrypted, mode='r:*') as nested:
      yield nested

  @staticmethod
  def read_gzip_struct(\
    member_name: str,\
    member_size: int,\
    member_mtime: int | float,\
    ftype: str,\
    backup_file: str\
  ) -> dict:
    try:
      reader = TarReader()
      with TarFile.open(backup_file, 'r:*') as local_tar, \
           reader.open_gzip(local_tar, member_name) as nested:
        files = reader.read_tar_metadata(nested)
        return FsMember(member_name, ftype, files, member_size, member_mtime).__dict__
    except Exception as e:
      traceback.print_exception(type(e), e, e.__traceback__)
      return {
        "name": member_name,
        "error": traceback.format_exc()
      }

  def get_gzip_members(
    self,
    tar_file: TarFile,
    members: list[TarInfo],
    file_type: str
  ) -> list[dict]:
    if not members:
      return []
    with ProcessPoolExecutor(max_workers=self._cpu_count) as executor:
      results = [None] * len(members)
      futures = {
        executor.submit(\
          TarReader.read_gzip_struct,\
          member.name,\
          member.size,\
          member.mtime,\
          file_type,\
          tar_file.name\
        ): i for i, member in enumerate(members)
      }
      for future in as_completed(futures):
        idx = futures[future]
        try:
          results[idx] = future.result()
        except Exception as e:
          traceback.print_exception(type(e), e, e.__traceback__)
          results[idx] = {
            "name": members[idx],
            "error": str(e)
          }
      return results

  @staticmethod
  def read_tar_struct(directory, fname):
    try:
      full_path = os.path.join(directory, fname)
      with TarFile.open(full_path, 'r:*') as backup_file:
        size = os.path.getsize(full_path)
        mtime = os.path.getmtime(full_path)
        reader = TarReader()
        files = reader.read_tar_metadata(backup_file)
        return FsMember(fname, 'backup', files, size, mtime).__dict__
    except Exception as e:
      traceback.print_exception(type(e), e, e.__traceback__)
      return {"name": fname, "error": traceback.format_exc()}

  def is_encrypted(self, backup_json: IO[bytes]) -> bool:
    manifest = json.load(backup_json)
    assert manifest['version'] == 2, 'Only manifest version 2 is supported.'
    if manifest['protected']:
      assert manifest['crypto'] == 'aes128', 'Only AES-128 encryption is supported.'
    return manifest['protected']

  def read_backup_dir(self) -> list[dict]:
    backup_dir = next(iter(self._passwords))
    members = [
      backups
      for backups in sorted(os.listdir(backup_dir))
      if backups.lower().endswith(self._archive_ext) \
        and os.path.isfile(os.path.join(backup_dir, backups))
    ]

    if not members:
      return [FsMember(backup_dir, 'root').__dict__]

    if not hasattr(self, '_shared_executor'):
      self._shared_executor = ProcessPoolExecutor(max_workers=self._cpu_count)

    files = [None] * len(members)
    futures = {
      self._shared_executor.submit\
        (TarReader.read_tar_struct, backup_dir, fname): i
      for i, fname in enumerate(members)
    }
    for future in as_completed(futures):
      idx = futures[future]
      try:
        files[idx] = future.result()
      except Exception as e:
        traceback.print_exception(type(e), e, e.__traceback__)
        files[idx] = {
          "name": members[idx],
          "error": str(e)
        }
    return [FsMember(backup_dir, 'root', files).__dict__]


class FsMember:
  def __init__(\
    self, name: str,\
    ftype: str,\
    files: list[object] = None,\
    size: int = None,\
    mtime:  int | float = None\
  ):
    self.name = os.path.normpath(name)
    self.type = ftype
    self.size = size
    if mtime:
      self.mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
    if files:
      self.files = files
