import logging, os, platform, posixpath, subprocess, shlex, string, sys

from docutils import nodes
from docutils.parsers.rst import directives, states
from docutils.parsers.rst.roles import set_classes

from sphinx.util.compat import Directive
from sphinx.util.osutil import ensuredir

from .phix import (PhixError,
                   program_files_32,
                   relfn2path,
                   temp_path)

log = logging.getLogger('phix.dia')
logging.basicConfig()

class dia(nodes.General, nodes.Element):
    '''A docutils node representing a Dia diagram'''

    def astext(self):
        '''
        Returns:
            The 'alt' text for the node as specified by the :alt: option on
            the dia directive.
        '''
        return self.get('alt', '')

class DiaDirective(Directive):
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
        return directives.choice(argument, directives.images.Image.align_values)

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True

    option_spec = {'postprocess'   : directives.unchanged,
                   'new-window' : directives.flag,
                   'alt': directives.unchanged,
                   'height': directives.length_or_unitless,
                   'width': directives.length_or_percentage_or_unitless,
                   'scale': directives.percentage,
                   'align': align,
                   'border': directives.positive_int,
                   'class': directives.class_option}

    def run(self):
        '''Process the dia directive.

        Creates and returns an list of nodes, including a dia node.
        '''

        log.info('self.arguments[0] = {0}'.format(self.arguments[0]))

        messages = []

        # Get the one and only argument of the directive which contains the
        # name of the Dia file.
        reference = directives.uri(self.arguments[0])
        env = self.state.document.settings.env
        _, filename = relfn2path(env, reference)

        log.info('filename = {0}'.format(filename))

        # Validate the :align: option
        if 'align' in self.options:
            if isinstance(self.state, states.SubstitutionDef):
                # Check for align_v_values.
                if self.options['align'] not in self.align_v_values:
                    raise self.error(
                        'Error in "{0}" directive: "{1}" is not a valid value '
                        'for the "align" option within a substitution '
                        'definition.  Valid values for "align" are: "{2}".'.format(
                            self.name,
                            self.options['align'],
                            '", "'.join(self.align_v_values)))
            elif self.options['align'] not in self.align_h_values:
                raise self.error(
                    'Error in "{0}" directive: "{1}" is not a valid value for '
                    'the "align" option.  Valid values for "align" are: "{2}".'.format(
                        self.name,
                        self.options['align'],
                        '", "'.join(self.align_h_values)))

        set_classes(self.options)

        log.info("self.block_text = {0}".format(self.block_text))
        log.info("self.options = {0}".format(self.options))

        dia_node = dia(self.block_text, **self.options)
        dia_node['uri'] = os.path.normpath(filename)
        dia_node['width'] = self.options['width'] if 'width' in self.options else '100%'
        dia_node['height'] = self.options['height'] if 'height' in self.options else '100%'
        dia_node['border'] = self.options['border'] if 'border' in self.options else 0
        dia_node['postprocess_command'] = self.options['postprocess'] if 'postprocess' in self.options else None
        dia_node['new_window_flag'] = 'new-window' in self.options

        log.info("dia_node['new_window_flag'] = {0}".format(
                dia_node['new_window_flag']))

        return messages + [dia_node]

def get_image_filename(self, uri):
    '''
    Get paths of output file.

    Args:
        uri: The URI of the source Dia file

    Returns:
        A 2-tuple containing two paths.  The first is a relative URI which can
        be used in the output HTML to refer to the produced image file. The
        second is an absolute path to which the generated image should be
        rendered.
    '''
    uri_dirname, uri_filename = os.path.split(uri)
    uri_basename, uri_ext = os.path.splitext(uri_filename)
    fname = '{0}.svg'.format(uri_basename)

    log.info('fname = {0}'.format(fname))

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

def create_graphics(self, dia_uri, render_path, postprocess_command=None):
    '''
    Use Dia in batch mode to render a diagram from a dia file into graphics of
    the specified format.

    Args:
        dia_uri:  The path to the Dia file.

        render_path: The path to which the graphics output is to be rendered.

        postprocess_command: An optional command into which the Dia SVG
           output will be piped before it is placed in the output document.
           The command should accept SVG on stdin and produce SVG on stdout.

    Raises:
        PhixError: If the graphics could not be rendered.
    '''

    log.info("create_graphics()")
    log.info("dia_uri = {0}".format(dia_uri))
    log.info("render_path = {0}".format(render_path))

    output_path = render_path if postprocess_command is None else temp_path('.svg')
    log.info("output_path = {0}".format(output_path))

    # Launch Dia and instruct it to export the diagram as SVG
    args = [str(dia_uri),
            '-e', str(output_path)]
    command = dia_command() + args
    log.info("command = {0}".format(command))
    returncode = subprocess.call(command)
    log.info("returncode = {0}".format(returncode))
    if returncode != 0:
        raise PhixError("Could not launch Dia with command {0}".format(' '.join(command)))

    # If a postprocess command has been specified
    if postprocess_command is not None:
        log.info("postprocess_command = {0}".format(postprocess_command))

        # We use our own variable interpolation with the $VAR syntax rather than
        # relying on the underlying shell, so that we can support the same
        # variable syntax on both Windows and Linux.
        postprocess_command_template = string.Template(str(postprocess_command))
        interpolated_postprocess_command = postprocess_command_template.substitute(os.environ)
        log.info("interpolated_postprocess_command = {0}".format(
                interpolated_postprocess_command))

        postprocess_command_fragments = shlex.split(interpolated_postprocess_command, posix=False)
        log.info("postprocess_command_fragments = {0}".format(
                postprocess_command_fragments))

        with open(output_path, 'rb') as intermediate_file:
            with open(render_path, 'wb') as render_file:
                returncode = subprocess.call(postprocess_command_fragments, stdin=intermediate_file, stdout=render_file)
                log.info("returncode = {0}".format(returncode))
                if returncode != 0:
                    raise PhixError("Could not launch postprocess with command {0}".format(' '.join(postprocess_command)))
        if os.path.exists(output_path):
            log.info("Removing {0}".format(output_path))
            os.remove(output_path)

def dia_command():
    '''Get a command for launching Dia.

    Returns a list based on the DIA_LAUNCH environment variable if set. This
    will be used as the basis for the list of arguments that is returned.
    Otherwise, it takes a guess at something that will work for the platform.

    Returns:
        A list of command line arguments - the first of which is an executable
        name or alias - which when passed to a shell can be used to launch
        dia.
    '''
    if 'DIA_LAUNCH' in os.environ:
        return shlex.split(os.environ['DIA_LAUNCH'])

    if platform.system() == 'Windows':
        # This is the location used by the Dia installer for Windows
        return [os.path.join(program_files_32(), "Dia", "bin", "diaw.exe")]

    return ['dia']

def render_html(self, node):
    '''
    Render the supplied node as HTML.

    Note: This method *always* raises docutils.nodes.SkipNode to ensure that the
        child nodes are not visited.

    Args:
        node: An dia docutils node.

    Raises:
        SkipNode: Do not visit the current node's children, and do not call the
        current node's ``depart_...`` method.
    '''
    has_thumbnail = False

    try:
        refer_path, render_path = get_image_filename(self, node['uri'])
        log.info("refer_path = {0}".format(refer_path))
        log.info("render_path = {0}".format(render_path))
        log.info("node['uri'] = {0}".format(node['uri']))
        #if not os.path.isfile(render_path):
        create_graphics(self, node['uri'], render_path, node.get('postprocess'))
    except PhixError:
        exc = sys.exc_info()
        log.info('Could not render {0}'.format(node['uri']),
                 exc_info = exc)
        self.builder.warn('Could not render {0} because of {1}'.format(
                node['uri'],
                exc[1]))
        raise nodes.SkipNode

    self.body.append(self.starttag(node, 'p', CLASS='dia'))

    objtag_format = '<object data="%s" width="%s" height="%s" border="%s" type="image/svg+xml" class="img">\n'
    self.body.append(objtag_format % (refer_path, node['width'], node['height'], node['border']))
    self.body.append('</object>')

    if node['new_window_flag']:
        self.body.append('<p align="right">\n')
        new_window_tag_format = '<a href="{0}" target="_blank">Open in new window</a>'
        self.body.append(new_window_tag_format.format(refer_path))
        self.body.append('</p>\n')

    self.body.append('</p>\n')
    raise nodes.SkipNode

def html_visit_dia(self, node):
    '''Visit an dia node during HTML rendering.'''
    render_html(self, node)

def latex_visit_dia(self, node):
    '''Visit an dia node during latex rendering.'''
    render_latex(self, node, node['code'], node['options'])

def setup(app):
    '''Register the services of this plug-in with Sphinx.'''
    app.add_node(dia,
        html=(html_visit_dia, None))
    app.add_directive('dia', DiaDirective)
