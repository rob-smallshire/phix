.. Phix documentation master file, created by
   sphinx-quickstart on Mon Jul 11 16:01:45 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Phix
===============

Phix is a Sphinx extension for embedding ArgoUML diagrams into Sphinx output.
Phix extends Sphinx by providing a single additional directive which allows
specification of an ArgoUML zargo file and the name of a diagram within that
file.  The most basic usage is::

  .. argouml:: my_uml_model.zargo
     :diagram: My Class Diagram
     
which will result in a single diagram being placed in the rendered HTML output
from Sphinx.

Usually, other options will be used with the ArgoUML directive to control the
output::

  .. argouml:: my_uml_model.zargo
     :diagram: My Sequence Diagram
     :width: 100%
     :height: 800 px
     :new-window:
     
The full list of supported options is:

  * `diagram` - compulsory option for specifying the name of the diagram which
    is to be included.
    
  * `width` - the width of the diagram, either as a percentage or in absolute
    units such as pixels.  Any units which can be used in HTML can be used here.
    
  * `height` - the height of the diagram, either as a percentage or in absolute
    units such as pixels.  Any units which can be used in HTML can be used here.
    
  * `new-window` - an optional flag which takes no arguments.  If present, a
    link `Open in new window` will be added underneath the rendered diagram.
    
  * `align` - Can take the values `left`, `right`, `center`.
  
  * `alt` - Alternative text to be used if the diagram cannot be rendered.
  
Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

