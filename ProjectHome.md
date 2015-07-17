# What is Phix for? #

Phix is a Sphinx extension which allows you to use diagrams from popular diagramming tools directly with Sphinx.  Phix supports,

  * ArgoUML - extract specific diagrams from a `.zargo` file as SVG.
  * Inkscape - extract simplified SVG for the web, from an Inkscape SVG file.
  * Dia - extract SVG from a `.dia` file.
  * Web Sequence Diagram - convert a textual description of a sequence diagram into an SVG diagram using the WSD server **you** provide.

Other diagramming tools will be added if there is demand.

# How to get it #

Use the download link to the left.  Unzip the archive, and then:

```
  $ cd phix-0.6dev-20110818
  $ python setup.py install
```

# How to enable it #

Register the Phix plug-in with your Sphinx project by modifying the `conf.py` file in your  documentation source. For example, here we have added Phix to the list of extensions used by a project.

```
# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.intersphinx',
              'sphinx.ext.todo',

              # From http://code.google.com/p/phix/
              'phix.argouml',            # for argouml support
              'phix.dia',                # for dia support
              'phix.inkscape',           # for inkscape support
              'phix.websequencediagram'] # for websequencediagram support
```

# How to use it #

Refer to ArgoUML file and diagram names from within your ReStructuredText document like this:

```
  .. argouml:: my_uml_model.zargo
     :diagram: My Sequence Diagram
```

For more details see the documentation.



