# hack to capture stdout to a string, to test it
import re
import os
import subprocess
import io
import sys
from contextlib import contextmanager
import filecmp
import sports_schedule_sat as sss
from functools import partial

from ortools.sat.python import cp_model

def test_fixture_functions():
    model = cp_model.CpModel()

    opposing_fixtures = sss.opponent_fixtures(model,3,2,3)
    assert len(opposing_fixtures) == 3
    assert opposing_fixtures[0].Name() == 'fixture: day %i, home %i, away %i'%(2,3,0)
    assert opposing_fixtures[1].Name() == 'fixture: day %i, home %i, away %i'%(2,3,1)
    assert opposing_fixtures[2].Name() == 'fixture: day %i, home %i, away %i'%(2,3,2)

    home_fixtures = sss.home_fixtures(model,3,2)
    assert len(home_fixtures) == 3
    assert len(home_fixtures[0]) == 3
    assert len(home_fixtures[1]) == 3
    assert len(home_fixtures[2]) == 3

    assert home_fixtures[0][0].Name() == 'fixture: day %i, home %i, away %i'%(2,0,0)
    assert home_fixtures[0][2].Name() == 'fixture: day %i, home %i, away %i'%(2,0,2)
    assert home_fixtures[2][0].Name() == 'fixture: day %i, home %i, away %i'%(2,2,0)

    fixtures = sss.daily_fixtures(model,3,4)
    assert len(fixtures) == 4
    for i in range(4):
        assert len(fixtures[i]) == 3
        for ht in range(3):
            assert len(fixtures[i][ht]) == 3
            for at in range(3):
                # assert len(fixtures[i][ht][at]) == 3
                assert fixtures[i][ht][at].Name() == 'fixture: day %i, home %i, away %i'%(i,ht,at)

    at_home_d2 = sss.create_at_home_array(model,4,2)
    assert len(at_home_d2) == 4
    for i in range(4):
        assert at_home_d2[i].Name() == 'at_home: day 2, home %i' % i

    at_home = sss.daily_at_home(model,4,2)
    assert len(at_home) == 2
    for i in range(2):
        assert len(at_home[i]) == 4
        for t in range(4):
            assert at_home[i][t].Name() == 'at_home: day %i, home %i' % (i,t)
