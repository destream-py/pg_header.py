"""
Read the header of a PostgreSQL's custom dump.

Most of the code has been translated directly from pg_restore source code.
"""
import ctypes
from time import mktime
from datetime import datetime

Z_DEFAULT_COMPRESSION = (-1)

K_VERS_1_0 = (( (1 * 256 + 0) * 256 + 0) * 256 + 0)
K_VERS_1_2 = (( (1 * 256 + 2) * 256 + 0) * 256 + 0)     # Allow No ZLIB
K_VERS_1_4 = (( (1 * 256 + 4) * 256 + 0) * 256 + 0)     # Date & name in header
K_VERS_1_7 = (( (1 * 256 + 7) * 256 + 0) * 256 + 0)     # File Offset size in
                                                        # header
K_VERS_1_10 = (( (1 * 256 + 10) * 256 + 0) * 256 + 0)   # add tablespace


# Newest format we can read
K_VERS_MAX = (( (1 * 256 + 12) * 256 + 255) * 256 + 0)

ArchiveFormat = {
    'archUnknown' : 0,
    'archCustom' : 1,
    'archTar' : 3,
    'archNull' : 4,
    'archDirectory' : 5,
}


def ReadInt(AH):
    res = 0
    sign = 0            # Default positive
    bitShift = 0
    if AH.version > K_VERS_1_0:
        # Read a sign byte
        sign = AH.ReadBytePtr()
    for b in range(AH.intSize):
        bv = AH.ReadBytePtr() & 0xFF
        if bv != 0:
            res = res + (bv << bitShift)
        bitShift += 8;
    if sign:
        res = -res
    return res

def ReadStr(AH):
    l = ReadInt(AH)
    if l < 0:
        buf = None
    else:
        buf = ctypes.create_string_buffer(l + 1)
        if AH.ReadBufPtr(buf, l) != l:
            raise IOError("unexpected end of file")
        buf[l] = '\0'
    return buf

class ArchiveHandle(object):

    def __init__(self, fh):
        self.warnings = []
        self.FH = fh

    def ReadBufPtr(self, buf, size):
        if size > len(buf):
            raise IOError("buffer not big enough")
        local_buf = ctypes.create_string_buffer(size)
        bytes_read = self.FH.readinto(local_buf)
        buf[:size] = local_buf
        return bytes_read

    def ReadBytePtr(self):
        return ord(self.FH.read(1))

    def ReadHead(AH):
        tmpMag = ctypes.create_string_buffer(7)

        if AH.ReadBufPtr(tmpMag, 5) != 5:
            raise IOError("unexpected end of file")

        if not tmpMag[:5] == 'PGDMP':
            raise IOError("did not find magic string in file header")

        AH.vmaj = AH.ReadBytePtr()
        AH.vmin = AH.ReadBytePtr()

        if AH.vmaj > 1 or (AH.vmaj == 1 and AH.vmin > 0):
            AH.vrev = AH.ReadBytePtr()
        else:
            AH.vrev = 0

        AH.version = ((AH.vmaj * 256 + AH.vmin) * 256 + AH.vrev) * 256 + 0

        if AH.version < K_VERS_1_0 or AH.version > K_VERS_MAX:
            raise IOError("unsupported version (%d.%d) in file header"
                          % (AH.vmaj, AH.vmin))

        AH.intSize = AH.ReadBytePtr()
        if AH.intSize > 32:
            raise IOError("sanity check on integer size (%lu) failed"
                          % AH.intSize)

        if AH.intSize > ctypes.sizeof(ctypes.c_int):
            AH.warnings.append(
                "WARNING: archive was made on a machine with larger integers, "
                "some operations might fail\n")

        if (AH.version >= K_VERS_1_7):
            AH.offSize = AH.ReadBytePtr()
        else:
            AH.offSize = AH.intSize
        AH.format = AH.ReadBytePtr()
        if AH.format not in ArchiveFormat.values():
            raise IOError("unexpected format %d" % AH.format)

        if AH.version >= K_VERS_1_2:
            if AH.version < K_VERS_1_4:
                AH.compression = AH.ReadBytePtr()
            else:
                AH.compression = ReadInt(AH)
        else:
            AH.compression = Z_DEFAULT_COMPRESSION

        if AH.version >= K_VERS_1_4:
            sec = ReadInt(AH)
            min = ReadInt(AH)
            hour = ReadInt(AH)
            mday = ReadInt(AH)
            mon = ReadInt(AH)
            year = ReadInt(AH)
            isdst = ReadInt(AH)
            crtm = datetime(
                (year + 1900), (mon + 1), mday, hour, min, sec, isdst)\
                .timetuple()

            AH.archdbname = ReadStr(AH).value

            AH.createDate = mktime(crtm)

            if AH.createDate == -1:
                self.warnings.append(
                    "WARNING: invalid creation date in header\n")

        if AH.version >= K_VERS_1_10:
            AH.archiveRemoteVersion = ReadStr(AH).value
            AH.archiveDumpVersion = ReadStr(AH).value
