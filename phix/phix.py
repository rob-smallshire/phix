import os
import posixpath
import subprocess
import shlex
import platform

from docutils import nodes, utils
from docutils import nodes
from docutils.parsers.rst import directives, states
from docutils.nodes import fully_normalize_name, whitespace_normalize_name
from docutils.parsers.rst.roles import set_classes

from sphinx.util.compat import Directive
from sphinx.util.osutil import ensuredir
from sphinx.errors import SphinxError

class PhixError(SphinxError):
    category = 'Phix error'

class argouml(nodes.General, nodes.Element):
    
    def astext(self):
        return self.get('alt', '')
    
# TODO: visit_argouml_node, depart_todo_node ?
    
class ArgoUmlDirective(Directive):
    # http://docutils.sourceforge.net/docs/howto/rst-directives.html

    align_h_values = ('left', 'center', 'right')
    align_v_values = ('top', 'middle', 'bottom')
    align_values = align_v_values + align_h_values

    def align(argument):
        # This is not callable as self.align.  We cannot make it a
        # staticmethod because we're saving an unbound method in
        # option_spec below.
        return directives.choice(argument, Image.align_values)

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {'diagram': directives.unchanged_required,
                   'alt': directives.unchanged,
                   'height': directives.length_or_unitless,
                   'width': directives.length_or_percentage_or_unitless,
                   'scale': directives.percentage,
                   'align': align,
                   'class': directives.class_option}
    
    
    
    def run(self):
        print "self.arguments[0] =", self.arguments[0]
        #print "self.arguments[1] =", self.arguments[1]
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
        messages = []
        reference = directives.uri(self.arguments[0])
        
        env = self.state.document.settings.env
        rel_filename, filename = relfn2path(env, reference)
        #print "rel_filename = ", os.path.normpath(rel_filename)
        print "filename = ", filename
        
        diagram = self.options['diagram']
        set_classes(self.options)
        print "self.block_text =", self.block_text
        print "self.options =", self.options    
        argouml_node = argouml(self.block_text, **self.options)
        argouml_node['uri'] = os.path.normpath(filename)
        argouml_node['diagram'] = diagram
        argouml_node['width'] = self.options['width'] if 'width' in self.options else '100%'
        argouml_node['height'] = self.options['height'] if 'height' in self.options else '100%'
        return messages + [argouml_node]

# compatibility to sphinx 1.0 (ported from sphinx trunk)
def relfn2path(env, filename, docname=None):
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
    """
    Get paths of output file.
    
    Args:
        uri: The URI of the source ArgoUML file
        
        diagram: The name of theh diagram within the ArgoUML file to be rendered.
    
    Returns:
        A 2-tuple containing two paths.  The first is a relative URI which can
        be used in the output HTML to refer to the produced image file. The
        second is an absolute path to which the generated image should be rendered.
    """
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

def create_graphics(self, zargo_uri, diagram_name, render_path):
    """
    Use ArgoUML in batch mode to render a named diagram from a zargo file into
    graphics of the specified format.
    
    Args:
        zargo_uri:  The path to the ArgoUML zargo file.
        
        diagram_name: A string containing the diagram name.
        
        render_path: The path to which the graphics output is to be rendered.
        
        format: The graphics format to be used. Default is svg.
    
    Raises:
        PhixError: If the graphics could not be rendered.
    """
    
    print "create_graphics()"
    print "zargo_uri =", zargo_uri
    print "diagram_name =", diagram_name
    print "render_path =", render_path

    args = ['-batch',
            '-command', 'org.argouml.uml.ui.ActionOpenProject=%s' % str(zargo_uri),
            '-command', 'org.argouml.ui.cmd.ActionGotoDiagram=%s' % str(diagram_name),
            '-command', 'org.argouml.uml.ui.ActionSaveGraphics=%s' % str(render_path)]
    command = argouml_command() + args
    print "command =", command
    returncode = subprocess.call(command, shell=True)
    print "returncode =", returncode

def argouml_command():
    '''Get a command for launching ArgoUML.
    
    Returns a list based on the ARGOUML_LAUNCH environment variable is set, this
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
               "-jar", r"C:\Program Files (x86)\ArgoUML\argouml.jar"]
               
    return ['argouml']
    
    
def render_html(self, node):
    has_thumbnail = False
    
    try:
        refer_path, render_path = get_image_filename(self, node['uri'], node['diagram'])
        print "refer_path =", refer_path
        print "render_path =", render_path
        print "node['uri'] =", node['uri']
        #if not os.path.isfile(render_path):
        create_graphics(self, node['uri'], node['diagram'], render_path)
    except PhixError, exc:
        print 'Could not render %s because %s' % (node['uri'], str(exc))
        self.builder.warn('Could not render %s because %s' % (node['uri'], str(exc)))
        raise nodes.SkipNode

    self.body.append(self.starttag(node, 'p', CLASS='argouml'))

    alt = "Blah"
    objtag_format = '<object data="%s" width="%s" height="%s" type="image/svg+xml" class="img">\n'
    self.body.append(objtag_format % (refer_path, node['width'], node['height']))
    self.body.append('</object>')
    self.body.append('</p>\n')
    raise nodes.SkipNode
        
def html_visit_argouml(self, node):
    render_html(self, node)

def latex_visit_argouml(self, node):
    render_latex(self, node, node['code'], node['options'])
    
def setup(app):
    app.add_node(argouml,
        html=(html_visit_argouml, None))
        #latex=(latex_visit_argouml, None))
    app.add_directive('argouml', ArgoUmlDirective)

