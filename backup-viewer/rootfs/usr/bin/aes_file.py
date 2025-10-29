import hashlib

import os

from Crypto.Cipher import AES

# AES-128 encryption as implemented by Secure Tar (https://github.com/pvizeli/securetar).
# - Encryption key is a password hashed 100 times with SHA-256 and cropped to 128 bits.
# - CBC mode is used, so the file is seekable. It's very useful, see below!
# - IV is derived from a seed appended to the key and hashed like the password.
# - IV seed is stored in the first 16 bytes or after a 32-byte header.
# - PKCS7 padding is used at the end.
#
# As of January 2025, Secure Tar also errorneously applies the padding before the last block. This
# breaks the CRC location in GZIP files. Luckily, we can correctly read the uncompressed size and
# Tarfile won't cross the EOF and won't trigger the CRC check. But it's a dumpster fire.


class AesFile:
  SECURETAR_MAGIC = b'SecureTar\x02\x00\x00\x00\x00\x00\x00'

  def __init__(self, password, file):
    self._key = AesFile._digest(password.encode())
    self._file = file
    self._start = file.tell()
    header = self._file.read(16)
    if header == AesFile.SECURETAR_MAGIC:
      self.size = int.from_bytes(file.read(8), 'big')
      self._start += 32
    else:
      self.size = file.seek(0, os.SEEK_END) - self._start - 16
      self.seek(-1, os.SEEK_END)
      self.size -= self.read(1)[0]
    self.seek(0)

  def _digest(key):
    for _ in range(100):
      key = hashlib.sha256(key).digest()
    return key[:16]

  def _init(self, block):
    self._file.seek(self._start + block * 16)
    iv = self._file.read(16)
    if block == 0:
      iv = AesFile._digest(self._key + iv)
    self._aes = AES.new(self._key, AES.MODE_CBC, iv)
    self._buf = b''

  def close(self) -> None:
    self._file.close()

  def _decrypt(self, blocks):
    return self._aes.decrypt(self._file.read(blocks * 16))

  def read(self, size):
    position = self.tell()
    if position + size > self.size:
      size = self.size - position
    assert size >= 0
    blocks = (size - len(self._buf) + 15) // 16
    assert blocks >= 0
    if blocks > 0:
      self._buf += self._decrypt(blocks)
    result = self._buf[:size]
    self._buf = self._buf[size:]
    return result

  def seek(self, offset, whence=os.SEEK_SET):
    if whence == os.SEEK_END:
      offset += self.size
    elif whence == os.SEEK_CUR:
      offset += self.tell()
    assert offset >= 0
    assert offset <= self.size
    self._init(offset // 16)
    remaining = offset % 16
    if remaining > 0:
      self._buf = self._decrypt(1)[remaining:]

  def tell(self):
    return self._file.tell() - self._start - 16 - len(self._buf)
