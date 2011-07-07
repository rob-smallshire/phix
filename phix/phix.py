
from docutils import nodes, utils
from docutils import nodes
from docutils.parsers.rst import directives, states
from docutils.nodes import fully_normalize_name, whitespace_normalize_name
from docutils.parsers.rst.roles import set_classes

from sphinx.util.compat import Directive
from sphinx.errors import SphinxError

class PhixError(SphinxError):
    category = 'Phix error'

class argouml(nodes.General, nodes.Element):
    pass
    
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
    required_arguments = 2
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {'alt': directives.unchanged,
                   'height': directives.length_or_unitless,
                   'width': directives.length_or_percentage_or_unitless,
                   'scale': directives.percentage,
                   'align': align,
                   'target': directives.unchanged_required,
                   'class': directives.class_option}
    
    
    
    def run(self):
        print "self.arguments[0] =", self.arguments[0]
        print "self.arguments[1] =", self.arguments[1]
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
        self.options['uri'] = reference
        reference_node = None
        if 'target' in self.options:
            block = states.escape2null(
                self.options['target']).splitlines()
            block = [line for line in block]
            target_type, data = self.state.parse_target(
                block, self.block_text, self.lineno)
            if target_type == 'refuri':
                reference_node = nodes.reference(refuri=data)
            elif target_type == 'refname':
                reference_node = nodes.reference(
                    refname=fully_normalize_name(data),
                    name=whitespace_normalize_name(data))
                reference_node.indirect_reference_name = data
                self.state.document.note_refname(reference_node)
            else:                           # malformed target
                messages.append(data)       # data is a system message
            del self.options['target']
        set_classes(self.options)
        image_node = nodes.image(self.block_text, **self.options)
        if reference_node:
            reference_node += image_node
            return messages + [reference_node]
        else:
            return messages + [image_node]

def setup(app):
    app.add_node(argouml)
    app.add_directive('argouml', ArgoUmlDirective)

