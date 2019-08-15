# hack to capture stdout to a string, to test it
import re
import os
import subprocess
import io
import sys
from contextlib import contextmanager
import filecmp


def test_rr_cases():

    # now for various combinations of inputs
    output_file = 'test_output.csv'

    # test exact round robin case, but just once
    process_command_line = ['python','src/sports_schedule_sat.py'
                            ,'-t','8'
                            ,'-d','7'
                            ,'-p','2'
                            ,'--cpu','2'
                            ,'--debug'
                            ,'--timelimit','10'
                            ,'--csv',output_file]
    try:
        proc = subprocess.run(process_command_line, encoding='utf8', capture_output=True)
        out = proc.stdout
        err = proc.stderr
        print('out 186 is ',out)
        assert re.search('OPTIMAL', out, re.MULTILINE)
        assert re.search('num_search_workers: 2',err,re.MULTILINE)
    except:
        assert False

    try:
        # clean up the temp file
        os.unlink(output_file)
    except:
        print('no file to delete')

    # test exact round robin case, but just twice around
    process_command_line = ['python','src/sports_schedule_sat.py'
                            ,'-t','4'
                            ,'-d','6'
                            ,'-p','1'
                            ,'--cpu','2'
                            ,'--debug'
                            ,'--timelimit','60'
                            ,'--csv',output_file]
    try:
        proc = subprocess.run(process_command_line, encoding='utf8', capture_output=True)
        out = proc.stdout
        err = proc.stderr
        assert re.search('OPTIMAL', out, re.MULTILINE)
        assert re.search('num_search_workers: 2',err,re.MULTILINE)
    except:
        assert False

    try:
        # clean up the temp file
        os.unlink(output_file)
    except:
        print('no file to delete')
