import os
import subprocess
import unittest

import phix.argouml
import phix.dia
import phix.inkscape
import phix.websequencediagram


test_dir = os.path.split(__file__)[0]

def build_project(project_name):
    '''Build and clean a sphix project in a given directory.

    This will throw an exception if either the build or clean of the
    project fails.

    Args:
      * project_name: The name of the directory containing the project
        to build.
    '''
    project_dir = os.path.join(test_dir, project_name)

    # The commands that will be executed, in order, in the project
    # directory.
    commands = [
        'make html',
        'make clean'
        ]

    # Save stdout in "<project_name>.stdout"
    with open('{}.stdout'.format(project_name), 'w') as stdout:
        # Save stderr in "<project_name>.stderr"
        with open('{}.stderr'.format(project_name), 'w') as stderr:

            # Run each command in turn.
            for command in commands:
                subprocess.check_call(
                    command.split(),
                    cwd=project_dir,
                    stdout=stdout,
                    stderr=stderr)

class Tests(unittest.TestCase):
    def test_dia(self):
        '''Build a project using the dia extension.
        '''
        build_project('dia_project')

    def test_argouml(self):
        '''Build a project using the argouml extension.
        '''
        build_project('argouml_project')

    def test_inkscape(self):
        '''Build a project using the inkscape extension.
        '''
        build_project('inkscape_project')

    def test_websequencediagrams(self):
        '''Build a project using the WSD extension.
        '''
        build_project('websequencediagram_project')

if __name__ == '__main__':
    unittest.main()

