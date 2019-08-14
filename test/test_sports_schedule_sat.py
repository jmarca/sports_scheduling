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

    # now for various combinations of inputs

    # 8 teams, 4 days, 4 pools
    process_command_line = ['python','src/sports_schedule_sat.py'
                            ,'-t','8'
                            ,'-d','4'
                            ,'-p','4'
                            ,'--csv',output_file]
    try:
        proc = subprocess.run(process_command_line, encoding='utf8', capture_output=True)
        out = proc.stdout
        err = proc.stderr
        print('out is ',out)
        assert re.search('OPTIMAL', out, re.MULTILINE)
        expected_file = 'test/data/output_t8_d4_p4.csv'
        assert filecmp.cmp(output_file,expected_file) != None
    except:
        assert False
    # clean up the temp file
    os.unlink(output_file)

    # test timelimit option, search option, debug option
    # 68 teams, 34 days, 4 pools
    process_command_line = ['python','src/sports_schedule_sat.py'
                            ,'-t','32'
                            ,'-d','30'
                            ,'-p','4'
                            ,'--debug'
                            ,'--cpu','1'
                            ,'--timelimit','1'
                            ,'--csv',output_file]
    try:
        proc = subprocess.run(process_command_line, encoding='utf8', capture_output=True)
        out = proc.stdout
        err = proc.stderr
        print('out is ',out)
        assert re.search('UNKNOWN', out, re.MULTILINE)
        assert re.search('Add more time using the --timelimit command line option', out, re.MULTILINE)
        assert re.search('num_search_workers: 1',err,re.MULTILINE)
    except:
        assert False

    # test timelimit option, search option, debug option
    process_command_line = ['python','src/sports_schedule_sat.py'
                            ,'-t','32'
                            ,'-d','30'
                            ,'-p','8'
                            ,'--debug'
                            ,'--cpu','4'
                            ,'--timelimit','1'
                            ,'--csv',output_file]
    try:
        proc = subprocess.run(process_command_line, encoding='utf8', capture_output=True)
        out = proc.stdout
        err = proc.stderr
        print('out is ',out)
        assert re.search('UNKNOWN', out, re.MULTILINE)
        assert re.search('Add more time using the --timelimit command line option', out, re.MULTILINE)
        assert re.search('num_search_workers: 4',err,re.MULTILINE)
    except:
        assert False

    # test not unknown, but still not optimal
    process_command_line = ['python','src/sports_schedule_sat.py'
                            ,'-t','32'
                            ,'-d','10'
                            ,'-p','4'
                            ,'--cpu','6'
                            ,'--debug'
                            ,'--timelimit','10'
                            ,'--csv',output_file]
    try:
        proc = subprocess.run(process_command_line, encoding='utf8', capture_output=True)
        out = proc.stdout
        err = proc.stderr
        print('out is ',out)
        assert re.search('FEASIBLE', out, re.MULTILINE)
        assert re.search(r"A better solution than \d+ might be found by adding more time using the --timelimit command line option", out, re.MULTILINE)
        assert re.search('num_search_workers: 6',err,re.MULTILINE)
    except:
        assert False

    try:
        # clean up the temp file
        os.unlink(output_file)
    except:
        print('no file to delete')



    # test exact round robin case, but just once
    process_command_line = ['python','src/sports_schedule_sat.py'
                            ,'-t','8'
                            ,'-d','7'
                            ,'-p','2'
                            ,'--cpu','6'
                            ,'--debug'
                            ,'--timelimit','10'
                            ,'--csv',output_file]
    try:
        proc = subprocess.run(process_command_line, encoding='utf8', capture_output=True)
        out = proc.stdout
        err = proc.stderr
        print('out is ',out)
        assert re.search('FEASIBLE', out, re.MULTILINE)
        assert re.search(r"A better solution than \d+ might be found by adding more time using the --timelimit command line option", out, re.MULTILINE)
        assert re.search('num_search_workers: 6',err,re.MULTILINE)
    except:
        assert False

    try:
        # clean up the temp file
        os.unlink(output_file)
    except:
        print('no file to delete')

    # test exact round robin case, but just twice around
    process_command_line = ['python','src/sports_schedule_sat.py'
                            ,'-t','8'
                            ,'-d','14'
                            ,'-p','2'
                            ,'--cpu','6'
                            ,'--debug'
                            ,'--timelimit','10'
                            ,'--csv',output_file]
    try:
        proc = subprocess.run(process_command_line, encoding='utf8', capture_output=True)
        out = proc.stdout
        err = proc.stderr
        print('out is ',out)
        assert re.search('OPTIMAL', out, re.MULTILINE)
        assert re.search('num_search_workers: 6',err,re.MULTILINE)
    except:
        assert False

    try:
        # clean up the temp file
        os.unlink(output_file)
    except:
        print('no file to delete')
