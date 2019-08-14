# hack to capture stdout to a string, to test it
import re
import os
import subprocess
import io
import sys
from contextlib import contextmanager
import filecmp

@contextmanager
def redirected(out=sys.stdout, err=sys.stderr):
    saved = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        yield
    finally:
        sys.stdout, sys.stderr = saved


def test_command_line_options():

    process_command_line = ['python','src/sports_schedule_sat.py']
    try:
        proc = subprocess.run(process_command_line)
        proc.check_returncode()
        print('failed to crash')
        assert False
    except:
        pass


    process_command_line = ['python','src/sports_schedule_sat.py'
                            ,'-t','2'
    ]
    try:
        proc = subprocess.run(process_command_line)
        proc.check_returncode()
        print('failed to crash')
        assert False
    except:
        pass

    process_command_line = ['python','src/sports_schedule_sat.py'
                            ,'-d','1']
    try:
        proc = subprocess.run(process_command_line)
        proc.check_returncode()
        print('failed to crash')
        assert False
    except:
        pass

    output_file = 'test_output.csv'
    process_command_line = ['python','src/sports_schedule_sat.py'
                            ,'-t','2'
                            ,'-d','2'
                            ,'--csv',output_file]
    try:
        proc = subprocess.run(process_command_line)
        proc.check_returncode()
        pass
    except:
        print('should not crash when called with -t and -d')
        assert False
    # clean up the temp file
    os.unlink(output_file)


    try:
        proc = subprocess.run(process_command_line, encoding='utf8', capture_output=True)
        out = proc.stdout
        err = proc.stderr
        print('out is ',out)
        assert re.search('OPTIMAL', out, re.MULTILINE)
        expected_file = 'test/data/output_t2_d2.csv'
        assert filecmp.cmp(output_file,expected_file) != None
    except:
        print('should not crash when called with -t and -d')
        assert False
    # clean up the temp file
    os.unlink(output_file)
