# based on sports_schedulting_sat.cc, Copyright 2010-2018 Google LLC
#
# translated to Python by James E. Marca August 2019, with the
# addition of some command line options, inter-pool play constraints,
# and CSV output dump
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Essentially a translation of sports_scheduling_sat.cc from the C++ example

I added CSV output option, and pool vs pool type constraints.

Code Climate gave my original code an F for maintainability, so I
refactored things heavily.  As a design principle, I'm deliberately
sticking with functional programming, not OO.  Aiming for no side
effects in my functions, and map/reduce, etc.  Not strictly possible
though, because mode.Add(<some constraint>) is by definition a side
effect.  Anyway, at this point the code is getting a grade of C from
Code Climate, so that's good enough.

"""
import argparse
import os
import re
import csv
from functools import partial
from functools import reduce

from ortools.sat.python import cp_model

class VarArraySolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, fixtures, getter, csvfile):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__fixtures = fixtures
        self.__getter = getter
        self.__solution_count = 0
        self.__writer = self.get_csv_writer(csvfile)
        self.__close_once = True

        fixture_regex = r"day (\d+), home (\d+), away (\d+)"
        self.__prog = re.compile(fixture_regex)

    def on_solution_callback(self):
        self.__solution_count += 1
        if self.__solution_count < 101:
            matches = self.__getter(solver=self,
                                    fixtures=self.__fixtures)
            # for vi in self.__fixtures:
            #     for vij in vi:
            #         for vijk in vij:
            #             if self.Value(vijk): # fixture is true, print the details
            #                 print('%s=%i' % (vijk, self.Value(vijk)), end='\n')
            #                 result = self.__prog.search('%s'%vijk)
            #                 #print(result.groups())
            #                 (d,h,a) = result.groups()
            #                 row = {"schedule":self.__solution_count,"day":d,"home":h,"away":a}
            #                 self.__writer.writerow(row)
            for row in matches:
                [print('%s=%i,' % (k,v),end=' ') for (k,v) in row.items()]
                print()
                self.__writer.writerow(row)

            print()
            self.__writer.writerow({})

        # elif self.__close_once:
        #     self.close_csv()

    def solution_count(self):
        return self.__solution_count

    def get_csv_writer(self,csvname):
        self.__csvfile = open(csvname, 'w', newline='')
        fieldnames = ['day','home','away','home pool','away pool']
        writer = csv.DictWriter(self.__csvfile, fieldnames=fieldnames)
        writer.writeheader()
        return writer

    # def close_csv(self):
    #     # if self.__close_once:
    #     #     os.close(self.__csvfile)
    #     #self.__close_once = False
    #  going to leak a file descriptor.  but I'm screwing up the close here

def get_scheduled_fixtures(solver,fixtures,pools):
    pool_membership = {home:homepool
                       for (homepool,pool) in enumerate(pools)
                       for home in pool}
    # away version of list is the same as home
    # away_details = home_details
    #
    # can't figure how to increment the game number inside the day
    # here, but I guess it is probably wrong anyway
    fixed_matches =  [{
        'day':day+1,
        'home':home+1,
        'away':away+1,
        'home pool':pool_membership[home]+1,
        'away pool':pool_membership[away]+1,
    }
                      for (day,fd) in enumerate(fixtures)
                      for (home,fh) in enumerate(fd)
                      for (away,fixture) in enumerate(fh)
                      if solver.Value(fixture)]
    return list(fixed_matches)

def check_file_collision(csv_basename):
    # check for any existing file
    idx = 1
    checkname = csv_basename
    match = re.search(r"\.csv", checkname)
    if not match:
        print ('looking for a .csv ending in passed in CSV file name.  Did not find it, so appending .csv to',csv_basename)
        csv_basename += ".csv"

    checkname = csv_basename
    while os.path.exists(checkname):
        checkname = re.sub(r"\.csv","_{}.csv".format(idx),csv_basename)
        idx += 1
        # or just get rid of it, but that is often undesireable
        # os.unlink(csv_basename)
    return checkname

def csv_dump_results(scheduled_games,csv_basename):

    checkname = check_file_collision(csv_basename)
    with open(checkname, 'w', newline='') as csvfile:
        fieldnames = ['day','home','away','home pool','away pool']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in scheduled_games:
            writer.writerow(row)





def accum_pool_pool(pool_vs_pool,row):
    pool_vs_pool[row['home pool']-1][row['away pool']-1] += 1
    return pool_vs_pool
def accum_team_pool(team_vs_pool, row):
    team_vs_pool[row['home']-1][row['away pool']-1] += 1
    team_vs_pool[row['away']-1][row['home pool']-1] += 1
    return team_vs_pool
def screen_dump_results(scheduled_games):

    for row in scheduled_games:
        [print('%s=%i,' % (k,v),end=' ') for (k,v) in row.items()]
        print()
    # for row in scheduled_games:
    #     print('day %i home %i away %i' %(row['day'],row['home'],row['away']))


def screen_dump_poolchecks(scheduled_games,pools):
    # next evaluate team vs pool, pool vs pool
    #
    # The expected values for these sums vary depending on problem parameters
    #
    # pool_vs_pool = []  # list of lists. These should be generally equal if i != j
    # team_vs_pool=[]  # list of lists. These should also be roughly equal
    # initialize both containers to zero values

    pool_vs_pool = [
        [0 for j in pools]
        for i in pools
    ]

    team_vs_pool=[
        [0 for pool in pools]
        for t in [team for pool in pools for team in pool]
    ]

    # this loop accumulates match counts for pool vs pool
    pool_vs_pool = reduce( accum_pool_pool, scheduled_games, pool_vs_pool)

    # this loop accumulates match counts for team vs pool
    team_vs_pool = reduce( accum_team_pool, scheduled_games, team_vs_pool)

    # this loop prints each team vs pool match counts
    [print('team %i (home or away) versus pool %i = %i' % (t+1,j,team_vs_pool[t][j]))
     for i in range(len(pools))
     for t in pools[i]
     for j in range(len(pools))]


    # this loop prints pool vs pool match counts
    all_combinations_sum = 0
    for i in range(len(pools)):
        for j in range(len(pools)):
            print('pool %i at home vs pool %i away, count = %i'%(i,j,pool_vs_pool[i][j]))
            all_combinations_sum += pool_vs_pool[i][j]
    total_games = len(scheduled_games)
    assert all_combinations_sum == total_games


def collect_pool_play_fixtures(teams,pools,matchdays,fixtures):
    pool_play=[
        [ fixture_slice(fixtures,matchdays,[t],pool) + fixture_slice(fixtures,matchdays,pool,[t])
          for pool in pools ]
        for t in teams
    ]
    return pool_play

def collect_pool_balance_fixtures(pools,matchdays,fixtures):
    pool_balance=[
        [ fixture_slice(fixtures,matchdays,pooli,poolj)
          for poolj in pools ]
        for pooli in pools
    ]
    return pool_balance

def fixture_slice(fixture,days,homes,aways):
    return [ fixture[day][home][a]  for day in days for home in homes for a in aways ]

def expected_t_vs_pool_games(t,pool):
    t_vs_pool = len(pool)
    if t in pool:
        t_vs_pool = len(pool) - 1
    return t_vs_pool

def expected_pool_vs_pool_games(pooli,poolj):
    if pooli[0] in poolj:
        return len(pooli)*(len(pooli) - 1)/2
    else:
        return len(pooli)*len(poolj)/2

def season_expected_games(games_per_rr,matchups_exact,matchups,total_games,unique_games):
    if matchups_exact:
        return int(matchups*games_per_rr)
    else:
        # figure correct ratio for uneven games remaining
        games_remaining = total_games - ((matchups-1)*unique_games)
        return int( (matchups-1)*games_per_rr +
                    games_remaining*games_per_rr//unique_games )


def add_pool_play_constraints(pools,pool_play,model,minimum_games_function):

    # games per round robin

    def constrain_games(triple):
        (t,ppi,pooli) = triple
        round_robin_games = expected_t_vs_pool_games(t,pooli)
        minimum_expected_games = minimum_games_function(games_per_rr=round_robin_games)
        model.Add(sum(pool_play[t][ppi]) >= minimum_expected_games)
        return (t,ppi,minimum_expected_games)
    result = list( map (constrain_games, [ (t,ppi,pooli)
                            for t in range(len(pool_play))
                            for (ppi,pooli) in enumerate(pools)]
    ))

def add_pool_balance_constraints(pools,pool_balance,model,minimum_games_function):

    # games per round robin

    def constrain_games(pair):
        (ppi,pooli,ppj,poolj) = pair
        round_robin_games = expected_pool_vs_pool_games(pooli,poolj)
        minimum_expected_games = minimum_games_function(games_per_rr=round_robin_games)

        # print(ppi,ppj,minimum_expected_games)

        if ppi==ppj:
            # softer constraint to allow for odd numbers
            model.Add(sum(pool_balance[ppi][ppj]) >= minimum_expected_games)
            model.Add(sum(pool_balance[ppi][ppj]) <= minimum_expected_games+1)
        else:
            # hard equality generally works okay here
            # now that I'm figuring the count properly
            model.Add(sum(pool_balance[ppi][ppj]) == minimum_expected_games)

        return (ppi,ppj,minimum_expected_games)
    result = list(map (constrain_games, [(ppi,pooli,ppj,poolj)
                            for (ppj,poolj) in enumerate(pools)
                            for (ppi,pooli) in enumerate(pools) ]
    ))

def add_one_game_per_day(matchdays,matches_per_day,teams,fixtures,model):
    # loop to list possible opponents for each team
    # each day, team t plays either home or away, but only once
    # or later, once becomes matches_per_day?
    # def model_add_sum_eq(model,l,v):
    #     model.Add(sum(l) == v)
    # fn = partial(model_add_sum_eq,model=model,v=1)
    # [fn(l=fixture_slice(fixtures,[d],[t],teams) + fixture_slice(fixtures,[d],teams,[t]))
    #  for d in matchdays for t in teams]
    # nope.  that is not at all clear.
    fn = partial(fixture_slice,fixtures)
    [ model.Add(sum(fn([d],[t],teams) + fn([d],teams,[t])) == 1)
      for d in matchdays
      for t in teams ]

def add_one_matchup_per_round_robin(teams,fixtures,model,matchups,matchups_exact,unique_games,matches_per_day,num_matchdays):
    days_to_play = int(unique_games // matches_per_day)
    fn = partial(fixture_slice,fixtures)
    # array of days in each round robin period
    rr_days = [
        [int(d+m*days_to_play) for d in range(days_to_play) ]
        for m in range(matchups-1)
    ]
    # using list comprehension for the side effect of calling model.Add
    # side effects are bad functional programming
    # but that's how it goes.
    #
    # the combination of
    #
    # fn(mdays,[t],[o]) + fn(mdays,[o],[t])
    #
    # represents all possible pairings of fixtures over the round
    # robin period between could probably between team t and team o.
    # The summed constraint forces just one of these fixtures to be
    # true, meaning each team plays just one team over a round robin
    # period
    #
    # I could probably streamline the function call to
    #
    # fn(mdays,[t,o],[t,o]), as i vs i is constrained to be always false
    #
    [ model.Add(sum(fn(mdays,[t],[o]) + fn(mdays,[o],[t]))==1)
      for t in teams
      for o in teams if t != o
      for mdays in rr_days
    ]


    # last (or possibly only if matchups==1) period might not have
    # full number of days_to_play required for a round robin
    last_days = [d for d in range( (matchups-1)*days_to_play,num_matchdays )]
    if matchups_exact:
        [ model.Add(sum(fn(last_days,[t],[o]) + fn(last_days,[o],[t]))==1)
          for t in teams
          for o in teams if t != o
        ]
    else:
        # in this case, there are not enough days for every team to
        # play every other team, so here I want to set a <=
        # constraint.  If it is == and there aren't enough days, then
        # the model is unsatisfiable.
        [ model.Add(sum(fn(last_days,[t],[o]) + fn(last_days,[o],[t]))<=1)
          for t in teams
          for o in teams if t != o
        ]

def add_max_home_stand_constraint(teams,at_home,model,num_matchdays,max_home_stand):
    # forbid sequence of 3 homes or 3 aways in a row
    for t in teams:
        for d in range(num_matchdays - max_home_stand):
            model.AddBoolOr([at_home[d+offset][t] for offset in range(max_home_stand+1)])
            model.AddBoolOr([at_home[d+offset][t].Not() for offset in range(max_home_stand+1)])
            # note, this works because AddBoolOr means at least one
            # element must be true.  if it was just AddBoolOr([home0,
            # home1, ..., homeN]), then that would mean that one or
            # all of these could be true, and you could have an
            # infinite sequence of home games.  However, that home
            # constraint is matched with an away constraint.  So the
            # combination says:
            #
            # AddBoolOr([home0, ... homeN]) at least one of these is true
            # AddBoolOr([away0, ... awayN]) at least one of these is true
            #
            # taken together, at least one home from 0 to N is true,
            # which means at least one away0 to awayN is false.  At
            # the same time, at least one away is true, which means
            # that the corresponding home is false.  So together, this
            # prevents a sequence of one more than max_home_stand to
            # take place.

def create_breaks(model,teams,num_matchdays):
    # note that I am careful to iterate the same way here and in
    # breaks_constraint, so that I don't have to double index breaks
    # as in breaks[d][t] or something
    breaks = [
        model.NewBoolVar('two home or two away for team %i, starting on matchday %i' % (t,d))
        for (breakidx,(t,d)) in enumerate([(t,d)
                                            for t in teams
                                            for d in range(num_matchdays-1)]) ]
    return breaks

def breaks_constraint(breaks,teams,at_home,num_matchdays,model,listall=False):
    # side effects through list comprehension, yet again
    [
        [model.AddBoolOr([at_home[d][t],at_home[d+1][t],breaks[breakidx]]),
         model.AddBoolOr([at_home[d][t].Not(),at_home[d+1][t].Not(),breaks[breakidx]]),

         model.AddBoolOr([at_home[d][t].Not(),at_home[d+1][t],breaks[breakidx].Not()]),
         model.AddBoolOr([at_home[d][t],at_home[d+1][t].Not(),breaks[breakidx].Not()])]
        for (breakidx,(t,d)) in enumerate([(t,d)
                                            for t in teams
                                            for d in range(num_matchdays-1)]) ]

    # I couldn't figure this out, so I wrote a little program
    # and proved it.  These effectively are identical to
    #
    # model.Add(at_home[d][t] == at_home[d+1][t]).OnlyEnforceIf(breaks[-1])
    # model.Add(at_home[d][t] != at_home[d+1][t]).OnlyEnforceIf(breaks[-1].Not())
    #
    # except they are a little more efficient, I believe.  Wrote it up in a blog post

    # literature aside, I'm finding in practice that is num_matchdays
    # is odd, this constraint is really hard (read: impossible) to meet.  So
    if listall:
        print('listall case')
        # in the list all case, want a hard constraint here (< is optimistic)
        if num_matchdays % 2:
            model.Add(sum(breaks) <= num_matchdays+1)
        else:
            model.Add(sum(breaks) <= num_matchdays)
    else:
        print('not listall case')
        if num_matchdays % 2:
            model.Add(sum(breaks) >= num_matchdays+1)
        else:
            model.Add(sum(breaks) >= num_matchdays)
    return breaks

def initialize_pools(num_pools,num_teams):
    pool_size = int(num_teams//num_pools)
    pools = [(list(range(int(g*pool_size),int((g+1)*pool_size)))) for g in range(num_pools-1)]
    # Last pool might need to be bigger.  If this ever gets used
    # in anger, the remainder should be spread over multiple
    # pools.
    pools.append(list(range(int((num_pools-1)*pool_size),num_teams)))
    return pools

def opponent_fixtures(model,num_teams,day,home_team):
    name_prefix = 'fixture: day %i, home %i, ' % (day,home_team)
    return [ model.NewBoolVar(name_prefix+'away %i'%away) for away in range(num_teams) ]

def home_fixtures(model,num_teams,day):
    opp_fix = partial(opponent_fixtures,model=model,num_teams=num_teams,day=day)
    result =  list( map( lambda x : opp_fix(home_team=x), list(range(num_teams)) ) )
    return result

def daily_thing(fn,model,num_teams,num_days):
    fixed = partial(fn,model=model,num_teams=num_teams)
    result = list(map(lambda x: fixed(day=x), list(range(num_days))))
    return result

def daily_fixtures(model, num_teams, num_days):
    return daily_thing(home_fixtures,
                       model=model,num_teams=num_teams,num_days=num_days)


def create_at_home_array(model,num_teams,day):
    name_prefix = 'at_home: day %i, ' % day
    return [ model.NewBoolVar(name_prefix+'home %i' % home) for home in range(num_teams) ]


def daily_at_home(model, num_teams, num_days):
    return daily_thing(create_at_home_array,
                       model=model,num_teams=num_teams,num_days=num_days)


def model_matches(num_teams,
                  num_matchdays,
                  num_matches_per_day,
                  num_pools,
                  max_home_stand,
                  listall
):

    model = cp_model.CpModel()

    matchdays = range(num_matchdays)
    matches = range(num_matches_per_day)
    teams = range(num_teams)
    # how many possible unique games?
    unique_games = (num_teams)*(num_teams-1)/2

    # how many games are possible to play
    total_games = num_matchdays * num_matches_per_day

    # maximum possible games versus an opponent.  example, if 20
    # possible total games, and 28 unique combinations, then 20 // 28
    # +1 = 1.  If 90 total games (say 5 per day for 18 match days) and
    # 10 teams for 45 possible unique combinations of teams, then 90
    # // 45 + 1 = 3. Hmm.  Should be 2
    matchups = int((total_games // unique_games) + 1)
    # print(matchups)
    # there is a special case, if total games / unique games == total
    # games // unique games, then the constraint can be ==, not <=
    matchups_exact = False
    if (total_games % unique_games == 0):
        matchups_exact = True
        matchups = int(total_games // unique_games)

    print('expected matchups per pair',matchups, 'exact?',matchups_exact)

    fixtures = daily_fixtures(model,num_teams,num_matchdays) # all possible games
    at_home = daily_at_home(model,num_teams,num_matchdays) # all possible games

    # now for pool to pool, balance play
    # expected number is...um
    # number of pools cross number of pools divided into number of days to play
    pools = initialize_pools(num_pools,num_teams)

    # loop to forbid playing self and to link at_home[day][team] in
    # terms of fixtures
    #
    # Note this might have issues if byes are valid.  In that case, if
    # a team has a bye on a match day, it plays neither home nor away.
    # But at_home[d][t] == False implies away, when it might be a by
    # if the team t does not play that day
    #
    [ model.Add(fixtures[d][i][i] == 0) # forbid playing self
      for d in matchdays
      for i in teams ]

    # link at_home, fixtures
    [(model.AddImplication(fixtures[d][i][j], at_home[d][i]),
      model.AddImplication(fixtures[d][i][j], at_home[d][j].Not()))
      for d in matchdays
      for i in teams
      for j in teams
      if i != j]

    pool_play = collect_pool_play_fixtures(teams,pools,matchdays,fixtures)
    pool_balance = collect_pool_balance_fixtures(pools,matchdays,fixtures)

    minimum_games_function =  partial(season_expected_games,
                                      matchups=matchups,
                                      matchups_exact=matchups_exact,
                                      unique_games=unique_games,
                                      total_games=total_games)

    add_pool_play_constraints(pools,pool_play,model,minimum_games_function)

    add_pool_balance_constraints(pools,pool_balance,model,minimum_games_function)

    add_one_game_per_day(matchdays,num_matches_per_day,teams,fixtures,model)

    # each matchup between teams happens at most "matchups" times per season
    # want to add a constraint here to force alternating home and away for same team matchups
    # assert 0
    add_one_matchup_per_round_robin(teams,fixtures,model,matchups,matchups_exact,unique_games,num_matches_per_day,num_matchdays)

    add_max_home_stand_constraint(teams,at_home,model,num_matchdays,max_home_stand)

    breaks = create_breaks(model,teams,num_matchdays)

    breaks_constraint(breaks,teams,at_home,num_matchdays,model,listall)

    return (pools,fixtures,breaks,model)


def solve_model(model,
                time_limit=None,
                num_cpus=None,
                debug=None):
    # run the solver
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.log_search_progress = debug
    solver.parameters.num_search_workers = num_cpus

    # solution_printer = SolutionPrinter() # since we stop at first
    # solution, this isn't really
    # necessary I think
    status = solver.Solve(model)
    print('Solve status: %s' % solver.StatusName(status))
    print('Statistics')
    print('  - conflicts : %i' % solver.NumConflicts())
    print('  - branches  : %i' % solver.NumBranches())
    print('  - wall time : %f s' % solver.WallTime())
    return (solver,status)


def solution_search_model(model,fixtures,pools,
                          time_limit=None,
                          num_cpus=None,
                          debug=None,
                          csv=None):
    # run the solver
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.log_search_progress = debug
    # cannot search with multiple CPUs
    # solver.parameters.num_search_workers = num_cpus
    # Search and print out all solutions.
    solution_printer = VarArraySolutionPrinter(fixtures,
                                               partial(get_scheduled_fixtures,pools=pools),
                                               check_file_collision("list_"+csv))
    status = solver.SearchForAllSolutions(model, solution_printer)
    print('Solve status: %s' % solver.StatusName(status))
    print('Statistics')
    print('  - conflicts : %i' % solver.NumConflicts())
    print('  - branches  : %i' % solver.NumBranches())
    print('  - wall time : %f s' % solver.WallTime())
    print('  - solutions found: %i' % solution_printer.solution_count())
    return (solver,status)


def report_results(solver,status,fixtures,pools,num_teams,num_matchdays,time_limit=None,csv=None):

    if status == cp_model.INFEASIBLE:
        return status

    if status == cp_model.UNKNOWN:
        print('Not enough time allowed to compute a solution')
        print('Add more time using the --timelimit command line option')
        return status

    print('Optimal objective value: %i' % solver.ObjectiveValue())

    scheduled_games = get_scheduled_fixtures(solver,fixtures,pools)

    screen_dump_results(scheduled_games)
    screen_dump_poolchecks(scheduled_games,pools)

    if status != cp_model.OPTIMAL and solver.WallTime() >= time_limit:
        print('Please note that solver reached maximum time allowed %i.' % time_limit)
        print('A better solution than %i might be found by adding more time using the --timelimit command line option'% solver.ObjectiveValue())


    if csv:
        csv_dump_results(scheduled_games,csv)

def cpu_guess_and_gripe(cpu):
    ncpu = len(os.sched_getaffinity(0))
    if not cpu:
        cpu = min(6,ncpu)
    print('Setting number of search workers to %i' % cpu)

    if cpu > ncpu:
        print('You asked for %i workers to be used, but the os only reports %i CPUs available.  This might slow down processing' % (cpu,ncpu))

    if cpu != 6:
        # don't whinge at user if cpu is set to 6
        if cpu < ncpu:
            print('Using %i workers, but there are %i CPUs available.  You might get faster results by using the command line option --cpu %i, but be aware ORTools CP-SAT solver is tuned to 6 CPUs' % (cpu,ncpu,ncpu))

        if cpu > 6:
            print('Using %i workers.  Be aware ORTools CP-SAT solver is tuned to 6 CPUs' % cpu)

    return cpu

def main():
    """Entry point of the program."""
    parser = argparse.ArgumentParser(description='Solve sports league match play assignment problem')
    parser.add_argument('-t,--teams', type=int, dest='num_teams', required=True,
                        help='Number of teams in the league')

    parser.add_argument('-d,--days', type=int, dest='num_matchdays', required=True,
                        help='Number of days on which matches are played.  Default is enough days such that every team can play every other team, or (number of teams - 1)')

    parser.add_argument('--matches_per_day', type=int, dest='num_matches_per_day',
                        help='Number of matches played per day.  Default is number of teams divided by 2.  If greater than the number of teams, then this implies some teams will play each other more than once.  In that case, home and away should alternate between the teams in repeated matchups.')

    parser.add_argument('-p,--pools', type=int, dest='num_pools',default=1,
                        help='How many separate pools should the teams be separated into.  Default is 1')

    parser.add_argument('--csv', type=str, dest='csv', default='output.csv',
                        help='A file to dump the team assignments.  Default is output.csv')

    parser.add_argument('--timelimit', type=int, dest='time_limit', default=60,
                        help='Maximum run time for solver, in seconds.  Default is 60 seconds.')

    parser.add_argument('--cpu',type=int,dest='cpu',
                        help='Number of workers (CPUs) to use for solver.  Default is 6 or number of CPUs available, whichever is lower')

    parser.add_argument('--debug', action='store_true',
                        help="Turn on some print statements.")

    parser.add_argument('--max_home_stand',type=int,dest='max_home_stand',default=2,
                        help="Maximum consecutive home or away games.  Default to 2, which means three home or away games in a row is forbidden.")

    parser.add_argument('--enumerate', action='store_true', dest='listall',
                        help="Enumerate all possible cases schedules, instead of finding just one.  This will create an absurd number of schedules for any reasonably-sized problem.")

    args = parser.parse_args()

    # set default for num_matchdays
    num_matches_per_day = args.num_matches_per_day
    if not num_matches_per_day:
        num_matches_per_day = args.num_teams // 2

    cpu = cpu_guess_and_gripe(args.cpu)

    # set up the model
    (pools,fixtures,breaks,model) = model_matches(args.num_teams,
                                                  args.num_matchdays,
                                                  num_matches_per_day,
                                                  args.num_pools,
                                                  args.max_home_stand,
                                                  args.listall)

    # pulled this out of model_matches to make it easier to collect
    # all possible matches
    #
    # let the solver minimize the number of breaks required to make
    # the schedule work
    #
    # But eventually make this a command line thing.

    minimize = False
    if not args.listall:
        model.Minimize(sum(breaks))


        (solver,status) = solve_model(model,
                                      args.time_limit,
                                      cpu,
                                      args.debug)
        report_results(solver,
                       status,
                       fixtures,
                       pools,
                       args.num_teams,
                       args.num_matchdays,
                       args.time_limit,
                       args.csv)
    else:
        (solver,status) = solution_search_model(model,fixtures,pools,
                                                args.time_limit,
                                                cpu,
                                                args.debug,
                                                args.csv)



if __name__ == '__main__':
    main()
