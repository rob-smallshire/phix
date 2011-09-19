import logging, os, platform, posixpath, subprocess, shlex, string

from docutils import nodes
from docutils.parsers.rst import directives, states
from docutils.parsers.rst.roles import set_classes

from sphinx.util.compat import Directive
from sphinx.util.osutil import ensuredir

from .phix import (PhixError,
                   program_files_32,
                   relfn2path,
                   temp_path)

log = logging.getLogger('phix.argouml')
logging.basicConfig()

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
        log.info('self.arguments[0] = {0}'.format(self.arguments[0]))

        messages = []

        # Get the one and only argument of the directive which contains the
        # name of the ArgoUML zargo file.
        reference = directives.uri(self.arguments[0])
        env = self.state.document.settings.env
        _, filename = relfn2path(env, reference)
        log.info('filename = {0}'.format(filename))

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

        log.info("self.block_text = {0}".format(self.block_text))
        log.info("self.options = {0}".format(self.options))

        argouml_node = argouml(self.block_text, **self.options)
        argouml_node['uri'] = os.path.normpath(filename)
        argouml_node['diagram'] = diagram
        argouml_node['width'] = self.options['width'] if 'width' in self.options else '100%'
        argouml_node['height'] = self.options['height'] if 'height' in self.options else '100%'
        argouml_node['border'] = self.options['border'] if 'border' in self.options else 0
        argouml_node['postprocess_command'] = self.options['postprocess'] if 'postprocess' in self.options else None
        argouml_node['new_window_flag'] = 'new-window' in self.options

        log.info("argouml_node['new_window_flag'] = {0}".format(
                argouml_node['new_window_flag']))

        return messages + [argouml_node]

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

    log.info("create_graphics()")
    log.info("zargo_uri = {0}".format(zargo_uri))
    log.info("diagram_name = {0}".format(diagram_name))
    log.info("render_path = {0}".format(render_path))

    output_path = render_path if postprocess_command is None else temp_path('.svg')
    log.info("output_path = {0}".format(output_path))

    # Launch ArgoUML and instruct it to export the requested diagram as SVG
    args = ['-batch',
            '-command', 'org.argouml.uml.ui.ActionOpenProject=%s' % str(zargo_uri),
            '-command', 'org.argouml.ui.cmd.ActionGotoDiagram=%s' % str(diagram_name),
            '-command', 'org.argouml.uml.ui.ActionSaveGraphics=%s' % str(output_path)]
    command = argouml_command() + args
    log.info("command = {0}".format(' '.join(command)))
    returncode = subprocess.call(command)
    log.info("returncode = {0}".format(returncode))
    if returncode != 0:
        raise PhixError("Could not launch ArgoUML with command %s" % ' '.join(command))

    # See if the output file doesn't exist. This is a good indicator
    # that the wrong diagram was selected in the directive.
    if not os.path.exists(output_path):
        raise PhixError(
            'The output SVG file {0} does not exist. This often means that you specified the wrong diagram in your argouml directive.'.format(
                output_path))

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

        with file(output_path, 'rb') as intermediate_file:
            with file(render_path, 'wb') as render_file:
                returncode = subprocess.call(postprocess_command_fragments, stdin=intermediate_file, stdout=render_file)
                log.info("returncode = {0}".format(returncode))
                if returncode != 0:
                    raise PhixError("Could not launch postprocess with command %s" % postprocess_command)
        if os.path.exists(output_path):
            log.info("Removing {0}".format(output_path))
            os.remove(output_path)

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
        log.info("refer_path = {0}".format(refer_path))
        log.info("render_path = {0}".format(render_path))
        log.info("node['uri'] = {0}".format(node['uri']))
        #if not os.path.isfile(render_path):
        create_graphics(self, node['uri'], node['diagram'], render_path, node.get('postprocess'))
    except PhixError, exc:
        log.info('Could not render {0} because {1}'.format(
                node['uri'], str(exc)))
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

def setup(app):
    '''Register the services of this phix plug-in with Sphinx.'''
    app.add_node(argouml,
        html=(html_visit_argouml, None))
        #latex=(latex_visit_argouml, None))
    app.add_directive('argouml', ArgoUmlDirective)
