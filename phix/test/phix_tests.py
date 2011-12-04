import os
import subprocess
import unittest

import phix.argouml
import phix.dia
import phix.inkscape
import phix.websequencediagram


test_dir = os.path.split(__file__)[0]

class Tests(unittest.TestCase):
    def test_dia(self):
        project_dir = os.path.join(test_dir, 'dia_project')

        commands = [
            'make html',
            'make clean'
            ]

        with open('dia_project.stdout', 'w') as stdout:
            with open('dia_project.stderr', 'w') as stderr:
                for command in commands:
                    subprocess.check_call(
                        command.split(),
                        cwd=project_dir,
                        stdout=stdout,
                        stderr=stderr)

if __name__ == '__main__':
    unittest.main()

