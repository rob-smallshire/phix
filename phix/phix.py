import os, tempfile

from sphinx.errors import SphinxError

class PhixError(SphinxError):
    '''The base Phix exception type.
    '''
    category = 'Phix error'

def relfn2path(env, filename, docname=None):
    '''Convert a filename into a relatve path and an absolute path.

    Args:
        env:

        filename: A relative path from the document to an external resource,
            such as an image.

        docname:

    Returns:
        A 2-tuple containing in the first element the relative path to filename
        from the document path, and in the second element
    '''
    # compatibility to sphinx 1.0 (ported from sphinx trunk)
    if filename.startswith('/') or filename.startswith(os.sep):
        rel_fn = filename[1:]
    else:
        docdir = os.path.dirname(env.doc2path(docname or env.docname,
                                              base=None))
        rel_fn = os.path.join(docdir, filename)
    try:
        return rel_fn, os.path.join(env.srcdir, rel_fn)
    except UnicodeDecodeError:
        # the source directory is a bytestring with non-ASCII characters;
        # let's try to encode the rel_fn in the file system encoding
        enc_rel_fn = rel_fn.encode(sys.getfilesystemencoding())
        return rel_fn, os.path.join(env.srcdir, enc_rel_fn)

def temp_path(suffix=''):
    '''Return a path to a temporary file. It is the responsibility of the
    calling code to ensure that the file is deleted.

    Args:
        suffix: Optional suffix for the temp file name.
    '''
    # It's not obvious that this is the 'right way to do it' in Python, but see
    # <http://stackoverflow.com/questions/5545473/temporary-shelves/5545638#5545638>
    fd, filename = tempfile.mkstemp(suffix)
    os.close(fd)
    return filename

def is_64_windows():
    return 'PROGRAMFILES(X86)' in os.environ

def program_files_32():
    if is_64_windows():
        return os.environ['PROGRAMFILES(X86)']
    else:
        return os.environ['PROGRAMFILES']

def program_files_64():
    if is_64_windows():
        return os.environ['PROGRAMW6432']
    else:
        return None


