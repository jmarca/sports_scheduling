# hack to capture stdout to a string, to test it
import re
import os
import subprocess
import io
import sys
from contextlib import contextmanager
import filecmp


def test_solution_listing():

    # now for various combinations of inputs
    output_file = 'test_output.csv'

    # test writing a list of solutions
    process_command_line = ['python','src/sports_schedule_sat.py'
                            ,'-t','4'
                            ,'-d','3'
                            ,'-p','1'
                            ,'--cpu','2'
                            ,'--debug'
                            ,'--timelimit','10'
                            ,'--csv',output_file
                            ,'--enumerate']
    try:
        proc = subprocess.run(process_command_line, encoding='utf8', capture_output=True)
        out = proc.stdout
        err = proc.stderr
        assert re.search(r"^day=\d, home=\d, away=\d, home pool=\d, away pool=\d$",
                         out, re.MULTILINE)
        assert re.search(r"#144", err, re.MULTILINE)
        assert not re.search(r"#145", err, re.MULTILINE)
        assert re.search('OPTIMAL', err, re.MULTILINE)
        assert not re.search('num_search_workers: 2',err,re.MULTILINE)
        expected_file = 'test/data/list_output_t4_d3_p1.csv'
        assert filecmp.cmp('list_'+output_file,expected_file) != None
    except:
        assert False

    try:
        # clean up the temp file
        os.unlink('list_'+output_file)
    except:
        print('no file to delete')

    # test writing a list of solutions, not a round robin case
    process_command_line = ['python','src/sports_schedule_sat.py'
                            ,'-t','4'
                            ,'-d','2'
                            ,'-p','2'
                            ,'--cpu','2'
                            ,'--debug'
                            ,'--timelimit','10'
                            ,'--csv',output_file
                            ,'--enumerate']
    try:
        proc = subprocess.run(process_command_line, encoding='utf8', capture_output=True)
        out = proc.stdout
        err = proc.stderr
        assert re.search('#24', err, re.MULTILINE)
        assert not re.search('#25', err, re.MULTILINE)
        assert re.search('OPTIMAL', err, re.MULTILINE)
        assert not re.search('num_search_workers: 2',err,re.MULTILINE)
        expected_file = 'test/data/list_output_t4_d2_p2.csv'
        assert filecmp.cmp('list_'+output_file,expected_file) != None
    except:
        assert False

    try:
        # clean up the temp file
        os.unlink('list_'+output_file)
    except:
        print('no file to delete')
