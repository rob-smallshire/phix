import os
import posixpath
import subprocess
import shlex
import platform
import tempfile
import string

from docutils import nodes, utils
from docutils import nodes
from docutils.parsers.rst import directives, states
from docutils.nodes import fully_normalize_name, whitespace_normalize_name
from docutils.parsers.rst.roles import set_classes

from sphinx.util.compat import Directive
from sphinx.util.osutil import ensuredir
from sphinx.errors import SphinxError


class PhixError(SphinxError):
    '''The base Phix exception type.
    '''
    category = 'Phix error'


class argouml(nodes.General, nodes.Element):
    '''A docutils node representing an ArgoUML diagram'''

    def astext(self):
        '''
        Returns:
            The 'alt' text for the node as specified by the :alt: option on
            the argouml directive.
        '''
        return self.get('alt', '')


class ArgoUmlDirective(Directive):
    '''The argouml directive.

    The implementation of directives is covered at
      http://docutils.sourceforge.net/docs/howto/rst-directives.html
    '''
    align_h_values = ('left', 'center', 'right')
    align_v_values = ('top', 'middle', 'bottom')
    align_values = align_v_values + align_h_values

    def align(argument):
        '''Convert and validate the :align: option.

        Args:
            argument: The argument passed to the :align: option.
        '''
        # This is not callable as self.align.  We cannot make it a
        # staticmethod because we're saving an unbound method in
        # option_spec below.
        return directives.choice(argument, Image.align_values)

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True

    option_spec = {'diagram': directives.unchanged_required,
                   'postprocess'   : directives.unchanged,
                   'new-window' : directives.flag,
                   'alt': directives.unchanged,
                   'height': directives.length_or_unitless,
                   'width': directives.length_or_percentage_or_unitless,
                   'scale': directives.percentage,
                   'align': align,
                   'border': directives.positive_int,
                   'class': directives.class_option}

    def run(self):
        '''Process the argouml directive.

        Creates and returns an list of nodes, including an argouml node.
        '''
        print "self.arguments[0] =", self.arguments[0]

        messages = []

        # Get the one and only argument of the directive which contains the
        # name of the ArgoUML zargo file.
        reference = directives.uri(self.arguments[0])
        env = self.state.document.settings.env
        _, filename = relfn2path(env, reference)
        print "filename = ", filename

        # Get the name of the diagram from the required :diagram: option
        diagram = self.options['diagram']

        # Validate the :align: option
        if 'align' in self.options:
            if isinstance(self.state, states.SubstitutionDef):
                # Check for align_v_values.
                if self.options['align'] not in self.align_v_values:
                    raise self.error(
                        'Error in "%s" directive: "%s" is not a valid value '
                        'for the "align" option within a substitution '
                        'definition.  Valid values for "align" are: "%s".'
                        % (self.name, self.options['align'],
                           '", "'.join(self.align_v_values)))
            elif self.options['align'] not in self.align_h_values:
                raise self.error(
                    'Error in "%s" directive: "%s" is not a valid value for '
                    'the "align" option.  Valid values for "align" are: "%s".'
                    % (self.name, self.options['align'],
                       '", "'.join(self.align_h_values)))

        set_classes(self.options)

        print "self.block_text =", self.block_text
        print "self.options =", self.options

        argouml_node = argouml(self.block_text, **self.options)
        argouml_node['uri'] = os.path.normpath(filename)
        argouml_node['diagram'] = diagram
        argouml_node['width'] = self.options['width'] if 'width' in self.options else '100%'
        argouml_node['height'] = self.options['height'] if 'height' in self.options else '100%'
        argouml_node['border'] = self.options['border'] if 'border' in self.options else 0
        argouml_node['postprocess_command'] = self.options['postprocess'] if 'postprocess' in self.options else None
        argouml_node['new_window_flag'] = 'new-window' in self.options
        print "argouml_node['new_window_flag'] =", argouml_node['new_window_flag']
        return messages + [argouml_node]


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


def get_image_filename(self, uri, diagram):
    '''
    Get paths of output file.

    Args:
        uri: The URI of the source ArgoUML file

        diagram: The name of theh diagram within the ArgoUML file to be rendered.

    Returns:
        A 2-tuple containing two paths.  The first is a relative URI which can
        be used in the output HTML to refer to the produced image file. The
        second is an absolute path to which the generated image should be
        rendered.
    '''
    uri_dirname, uri_filename = os.path.split(uri)
    uri_basename, uri_ext = os.path.splitext(uri_filename)
    fname = '%s-%s.svg' % (uri_basename, diagram.replace(' ', '_'))
    print "fname =", fname
    if hasattr(self.builder, 'imgpath'):
        # HTML
        refer_path = posixpath.join(self.builder.imgpath, fname)
        render_path = os.path.join(self.builder.outdir, '_images', fname)
    else:
        # LaTeX
        refer_path = fname
        render_path = os.path.join(self.builder.outdir, fname)

    if os.path.isfile(render_path):
        return refer_path, render_path

    ensuredir(os.path.dirname(render_path))

    return refer_path, render_path


def create_graphics(self, zargo_uri, diagram_name, render_path, postprocess_command=None):
    '''
    Use ArgoUML in batch mode to render a named diagram from a zargo file into
    graphics of the specified format.

    Args:
        zargo_uri:  The path to the ArgoUML zargo file.

        diagram_name: A string containing the diagram name.

        render_path: The path to which the graphics output is to be rendered.

        postprocess_command: An optional command into which the ArgoUML SVG
           output will be piped before it is placed in the output document.
           The command should accept SVG on stdin and produce SVG on stdout.

    Raises:
        PhixError: If the graphics could not be rendered.
    '''

    print "create_graphics()"
    print "zargo_uri =", zargo_uri
    print "diagram_name =", diagram_name
    print "render_path =", render_path

    output_path = render_path if postprocess_command is None else temp_path('.svg')
    print "output_path =", output_path

    # Launch ArgoUML and instruct it to export the requested diagram as SVG
    args = ['-batch',
            '-command', 'org.argouml.uml.ui.ActionOpenProject=%s' % str(zargo_uri),
            '-command', 'org.argouml.ui.cmd.ActionGotoDiagram=%s' % str(diagram_name),
            '-command', 'org.argouml.uml.ui.ActionSaveGraphics=%s' % str(output_path)]
    command = argouml_command() + args
    print "command =", command
    returncode = subprocess.call(command)
    print "returncode =", returncode
    if returncode != 0:
        raise PhixError("Could not launch ArgoUML with command %s" % ' '.join(command))

    # If a postprocess command has been specified
    if postprocess_command is not None:
        print "postprocess_command =", postprocess_command

        # We use our own variable interpolation with the $VAR syntax rather than
        # relying on the underlying shell, so that we can support the same
        # variable syntax on both Windows and Linux.
        postprocess_command_template = string.Template(str(postprocess_command))
        interpolated_postprocess_command = postprocess_command_template.substitute(os.environ)
        print "interpolated_postprocess_command =", interpolated_postprocess_command

        postprocess_command_fragments = shlex.split(interpolated_postprocess_command, posix=False)
        print "postprocess_command_fragments =", postprocess_command_fragments
        with file(output_path, 'rb') as intermediate_file:
            with file(render_path, 'wb') as render_file:
                returncode = subprocess.call(postprocess_command_fragments, stdin=intermediate_file, stdout=render_file)
                print "returncode =", returncode
                if returncode != 0:
                    raise PhixError("Could not launch postprocess with command %s" % ' '.join(postprocess_command))
        if os.path.exists(output_path):
            print "Removing", output_path
            os.remove(output_path)


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


def argouml_command():
    '''Get a command for launching ArgoUML.

    Returns a list based on the ARGOUML_LAUNCH environment variable if set. This
    will be used as the basis for the list of arguments that is returned.
    Otherwise, it takes a guess at something that will work for the platform.

    Returns:
        A list of command line arguments - the first of which is an executable
        name or alias - which when passed to a shell can be used to launch
        argouml.
    '''
    if 'ARGOUML_LAUNCH' in os.environ:
        return shlex.split(os.environ['ARGOUML_LAUNCH'])

    if platform.system() == 'Windows':
        # This is the location used by the ArgoUML installer for Windows
        # It requires that 'java' is available on the syatem %PATH%.
        return [r"java",
               "-Xms64m", "-Xmx512m",
               "-jar", os.path.join(program_files_32(), "ArgoUML", "argouml.jar")]

    return ['argouml']


def render_html(self, node):
    '''
    Render the supplied node as HTML.

    Note: This method *always* raises docutils.nodes.SkipNode to ensure that the
        child nodes are not visited.

    Args:
        node: An argouml docutils node.

    Raises:
        SkipNode: Do not visit the current node's children, and do not call the
        current node's ``depart_...`` method.
    '''
    has_thumbnail = False

    try:
        refer_path, render_path = get_image_filename(self, node['uri'], node['diagram'])
        print "refer_path =", refer_path
        print "render_path =", render_path
        print "node['uri'] =", node['uri']
        #if not os.path.isfile(render_path):
        create_graphics(self, node['uri'], node['diagram'], render_path, node.get('postprocess'))
    except PhixError, exc:
        print 'Could not render %s because %s' % (node['uri'], str(exc))
        self.builder.warn('Could not render %s because %s' % (node['uri'], str(exc)))
        raise nodes.SkipNode

    self.body.append(self.starttag(node, 'p', CLASS='argouml'))

    objtag_format = '<object data="%s" width="%s" height="%s" border="%s" type="image/svg+xml" class="img">\n'
    self.body.append(objtag_format % (refer_path, node['width'], node['height'], node['border']))
    self.body.append('</object>')

    if node['new_window_flag']:
        self.body.append('<p align="right">\n')
        new_window_tag_format = '<a href="%s" target="_blank">Open in new window</a>'
        self.body.append(new_window_tag_format % refer_path)
        self.body.append('</p>\n')

    self.body.append('</p>\n')
    raise nodes.SkipNode


def html_visit_argouml(self, node):
    '''Visit an argouml node during HTML rendering.'''
    render_html(self, node)


def latex_visit_argouml(self, node):
    '''Visit an argouml node during latex rendering.'''
    render_latex(self, node, node['code'], node['options'])

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
    

def setup(app):
    '''Register the services of this phix plug-in with Sphinx.'''
    app.add_node(argouml,
        html=(html_visit_argouml, None))
        #latex=(latex_visit_argouml, None))
    app.add_directive('argouml', ArgoUmlDirective)

