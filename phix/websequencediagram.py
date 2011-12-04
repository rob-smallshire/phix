'''Phix tool for rendering websequencediagrams as SVG.
'''

import logging
import os
import posixpath
import subprocess
import shlex
import re
import string
import sys

if sys.version_info.major == 2:
    from urllib import urlencode, urlopen, urlretrieve
else:
    from urllib.parse import urlencode
    from urllib.request import urlopen, urlretrieve

from docutils import nodes
from docutils.parsers.rst import directives, states
from docutils.parsers.rst.roles import set_classes

from sphinx.util.compat import Directive
from sphinx.util.osutil import ensuredir

from .phix import PhixError, relfn2path, temp_path

log = logging.getLogger('phix.websequencediagram')
logging.basicConfig()

class wsd(nodes.General, nodes.Element):
    '''A docutils node representing a websequencediagram diagram.'''

    def astext(self):
        '''
        Returns:
            The 'alt' text for the node as specified by the :alt: option on
            the websequencediagram directive.
        '''
        return self.get('alt', '')


class WSDDirective(Directive):
    '''The websequencediagram directive.

    The implementation of directives is covered at
      http://docutils.sourceforge.net/docs/howto/rst-directives.html
    '''
    align_h_values = ('left', 'center', 'right')
    align_v_values = ('top', 'middle', 'bottom')
    align_values = align_v_values + align_h_values

    style_values = ('default',
                    'earth',
                    'modern-blue',
                    'mscgen',
                    'omegapple',
                    'qsd',
                    'rose',
                    'roundgreen',
                    'napkin',
                    'rose',
                    'vs2010')

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
                   'class': directives.class_option,
                   'style': directives.unchanged,
                   'api-version':directives.unchanged,
                   'server-url':directives.unchanged}

    def run(self):
        '''Process the wsd directive.

        Creates and returns an list of nodes, including a wsd node.
        '''

        log.info('self.arguments[0] = {0}'.format(self.arguments[0]))

        messages = []

        # Get the one and only argument of the directive which contains the
        # name of the WSD source file.
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

        # validate :style: option
        if 'style' in self.options:
            if self.options['style'] not in self.style_values:
                raise self.error(
                    'Error in "{0}" directive: "{1}" is not a valid value '
                    'for the "style" option within a substitution '
                    'definition.  Valid values for "style" are: "{2}".'.format(
                        self.name,
                        self.options['style'],
                        '", "'.join(self.style_values)))

        set_classes(self.options)

        log.info("self.block_text = {0}".format(self.block_text))
        log.info("self.options = {0}".format(self.options))

        wsd_node = wsd(self.block_text, **self.options)
        wsd_node['uri'] = os.path.normpath(filename)
        wsd_node['width'] = self.options.get('width', '100%')
        wsd_node['height'] = self.options.get('height', '100%')
        wsd_node['border'] = self.options.get('border', 0)
        wsd_node['postprocess_command'] = self.options.get('postprocess', None)
        wsd_node['new_window_flag'] = 'new-window' in self.options
        wsd_node['style'] = self.options.get('style', 'vs2010')
        wsd_node['api_version'] = self.options.get('api-version', '1')
        wsd_node['server_url'] = self.options.get('server-url', None)

        log.info("wsd_node['new_window_flag'] = {0}".format(
                wsd_node['new_window_flag']))

        return messages + [wsd_node]

def get_image_filename(self, uri):
    '''
    Get paths of output file.

    Args:
        uri: The URI of the source WSD file

    Returns:
        A 2-tuple containing two paths.  The first is a relative URI which can
        be used in the output HTML to refer to the produced image file. The
        second is an absolute path to which the generated image should be
        rendered.
    '''

    # TODO: This appears to be pretty common across various
    # tools. Refactor it out of here and into phix.py.

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

def retrieve_diagram(text,
                     output_file,
                     style,
                     api_version,
                     server_url):
    '''Contact wsd server to create diagram from source text.

    Args:
      text: The source text.
      output_file: The name of the file into which to put the output.
      style: The style of the drawing. Options={style}.
      api_version: Version of WSD api to use.
      server_url: The URL of the WSD server.
    '''.format(style=WSDDirective.style_values)

    # See if the user overrode the server-url in the calling environment.
    try:
        server_url = os.environ['PHIX_WEBSEQUENCEDIAGRAM_SERVER']
    except KeyError:
        pass

    # Check that server URL is set.
    if not server_url:
        raise PhixError('Websequencediagram server not specified. Use either a ":server-url:" option or set PHIX_WEBSEQUENCEDIAGRAM_SERVER in your environment')

    request = {}
    request["message"] = text
    request["style"] = style
    request["apiVersion"] = api_version
    request['format'] = 'svg'

    url = urlencode(request)

    f = urlopen(server_url, url)
    line = f.readline()
    f.close()

    log.info('Server response: {0}'.format(
            line))

    expr = re.compile("(\?(png|pdf|svg)=[a-zA-Z0-9]+)")
    m = expr.search(line)

    if m == None:
        raise PhixError("Invalid response from server: {0}".format(line))

    urlretrieve(
        server_url + m.group(0),
        output_file)

def create_graphics(self,
                    wsd_uri,
                    render_path,
                    style,
                    api_version,
                    server_url,
                    postprocess_command):
    '''
    Use a websequencediagrams server to render a from a wsd text
    description file into graphics of the specified format.

    Args:
        wsd_uri:  The path to the wsd source file.

        render_path: The path to which the graphics output is to be rendered.

        postprocess_command: An optional command into which the WSD SVG
           output will be piped before it is placed in the output document.
           The command should accept SVG on stdin and produce SVG on stdout.

        style: The style of the rendering. Options = {styles}

        api_version: Version of WSD API to use (string).

        server_url: The URL of the WSD server to use.

    Raises:
        PhixError: If the graphics could not be rendered.
    '''.format(styles=WSDDirective.style_values)

    log.info("create_graphics()")
    log.info("wsd_uri = {0}".format(wsd_uri))
    log.info("render_path = {0}".format(render_path))

    output_path = render_path if postprocess_command is None else temp_path('.svg')
    log.info("output_path = {0}".format(output_path))

    # Contact a wsd server and instruct it to export the diagram as SVG
    with open(wsd_uri, 'r') as f:
        source_text = f.read()

    retrieve_diagram(
        text=source_text,
        output_file=output_path,
        style=style,
        api_version=api_version,
        server_url=server_url)

    # If a postprocess command has been specified
    # TODO: The logic for doing post-process commands is common
    # between many tools. It should be refactored.
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

def render_html(self, node):
    '''Render the supplied node as HTML.

    Note: This method *always* raises docutils.nodes.SkipNode to ensure that the
        child nodes are not visited.

    Args:
        node: An wsd docutils node.

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
        log.info('node["style"] = {0}'.format(node['style']))

        create_graphics(self,
                        wsd_uri=node['uri'],
                        render_path=render_path,
                        postprocess_command=node.get('postprocess'),
                        style=node['style'],
                        api_version=node['api_version'],
                        server_url=node['server_url'])
    except PhixError:
        exc = sys.exc_info()
        log.info('Could not render {0}'.format(node['uri']),
                 exc_info = exc)
        self.builder.warn('Could not render {0}'.format(node['uri']),
                          exc_info=exc)
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


def html_visit_wsd(self, node):
    '''Visit a wsd node during HTML rendering.'''
    render_html(self, node)


def latex_visit_wsd(self, node):
    '''Visit a wsd node during latex rendering.'''
    render_latex(self, node, node['code'], node['options'])

def setup(app):
    '''Register the services of this plug-in with Sphinx.'''
    app.add_node(
        wsd,
        html=(html_visit_wsd, None))
    app.add_directive(
        'websequencediagram',
        WSDDirective)
