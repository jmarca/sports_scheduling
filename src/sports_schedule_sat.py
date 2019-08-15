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

Added CSV output option, and pool vs pool type constraints

As a design principle, I'm deliberately sticking with functional
programming, not OO.  So no side effects, and map/reduce, etc

"""
import argparse
import os
import re
import csv
from functools import partial

from ortools.sat.python import cp_model



def csv_dump_results(solver,fixtures,pools,num_teams,num_matchdays,csv_basename):
    matchdays = range(num_matchdays)
    teams = range(num_teams)

    vcsv = []
    for d in matchdays:
        game = 0
        for homepool in range(len(pools)):
            for home in pools[homepool]:
                for awaypool in range(len(pools)):
                    for away in pools[awaypool]:
                        match_on = solver.Value(fixtures[d][home][away])
                        if match_on:
                            game += 1
                            # each row: day,game,home,away,homepool,awaypool
                            row = {'day':d+1,
                                   'game':game,
                                   'home':home+1,
                                   'away':away+1,
                                   'home pool':homepool+1,
                                   'away pool':awaypool+1}
                            vcsv.append(row)

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


    with open(checkname, 'w', newline='') as csvfile:
        fieldnames = ['day','game','home','away','home pool','away pool']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in vcsv:
            writer.writerow(row)


def screen_dump_results(solver,fixtures,pools,num_teams,num_matchdays):
    matchdays = range(num_matchdays)
    teams = range(num_teams)
    num_pools = len(pools)


    total_games = 0
    for d in matchdays:
        game = 0
        for home in teams:
            for away in teams:
                match_on = solver.Value(fixtures[d][home][away])
                if match_on:
                    game += 1
                    print('day %i game %i home %i away %i' %(d+1,game,home+1,away+1))
        total_games += game

    # next evaluate team vs pool, pool vs pool
    #
    # The expected values for these sums vary depending on problem parameters
    #
    pool_vs_pool = []  # list of lists. These should be generally equal if i != j
    team_pool_play=[]  # list of lists. These should also be roughly equal
    # initialize both containers to zero values
    for i in range(num_pools):
        pool_vs_pool.append([0 for j in range(num_pools)])
        for t in pools[i]:
            team_pool_play.append([])
            for j in range(num_pools):
                for other in pools[j]:
                    team_pool_play[t].append(0)

    # this loop accumulates match counts for team vs pool and pool vs pool
    for d in matchdays:
        for i in range(num_pools):
            for t in pools[i]:
                for j in range(num_pools):
                    for other in pools[j]:
                        home_match = solver.Value(fixtures[d][t][other])
                        away_match = solver.Value(fixtures[d][other][t])
                        if home_match:
                            # team t is home, playing vs pool j
                            team_pool_play[t][j] += 1
                            pool_vs_pool[i][j] += 1
                        if away_match:
                            # team t is away, but still playing vs pool j
                            team_pool_play[t][j] += 1

    # this loop prints each team vs pool match counts
    for i in range(num_pools):
        for t in pools[i]:
            for j in range(num_pools):
                print('team %i (home or away) versus pool %i = %i' % (t+1,j,team_pool_play[t][j]))

    # this loop prints pool vs pool match counts
    all_combinations_sum = 0
    for i in range(num_pools):
        for j in range(num_pools):
            print('pool %i at home vs pool %i away, count = %i'%(i,j,pool_vs_pool[i][j]))
            all_combinations_sum += pool_vs_pool[i][j]
    assert all_combinations_sum == total_games


def collect_pool_play_fixtures(teams,pools,matchdays,fixtures):
    pool_play=[]
    pool_balance=[]
    num_pools = len(pools)
    # prep the arrays
    for t in teams:
        pool_play.append([])
        for pool in pools:
            pool_play[t].append([])

    for ppi in pools:
        ppi_balance = []
        for ppj in pools:
            ppi_balance.append([])
        pool_balance.append(ppi_balance)


    for ppi in range(num_pools):
        for t in pools[ppi]:
            # other team pool is inner loop
            for ppj in range(num_pools):
                # over all the days, have to play each pool at least once
                for d in matchdays:
                    for opponent in pools[ppj]:
                        if t == opponent:
                            # cannot play self
                            continue
                        # save case of t is home, playing vs pool j
                        pool_play[t][ppj].append(fixtures[d][t][opponent])
                        # save case of t is away, playing vs pool j
                        pool_play[t][ppj].append(fixtures[d][opponent][t])
                        # save pool home vs pool away case
                        pool_balance[ppi][ppj].append(fixtures[d][t][opponent])


    return (pool_play,pool_balance)

def add_pool_play_constraints(pools,pool_play,model,matchups,matchups_exact,unique_games,total_games):
    # pulling this out of the above loop for safety
    for t in range(len(pool_play)):
        for ppi in range(len(pools)):
            # over all the days, have to play each pool at least once
            # model.AddBoolOr(pool_play[t][ppj])
            # in order to require more than one, use Add(sum(...))

            # special case of playing versus own pool
            # because can't play against self
            my_size = len(pools[ppi])
            # this team vs all other teams, figure max games vs this pool
            pool_matchup_count = int(my_size)
            if t in pools[ppi]:
                # "other pool" is actually my pool.  can't play self
                pool_matchup_count = int((my_size-1))

            local_count = matchups*pool_matchup_count
            if not matchups_exact:
                # in this case, last round of matchups is not complete.  must play less
                games_remaining = total_games - ((matchups-1)*unique_games)
                # print(total_games,matchups,unique_games,games_remaining,pool_matchup_count,(games_remaining*pool_matchup_count//unique_games))
                # print(local_count,'becomes...')
                local_count = int((matchups-1)*pool_matchup_count + games_remaining*pool_matchup_count//unique_games)
                # print(local_count)
                    # assert 0
            model.Add(sum(pool_play[t][ppi]) >= local_count)

def add_pool_balance_constraints(pools,pool_balance,model,matchups,matchups_exact,unique_games,total_games):
    num_pools = len(pools)
    for ppi in range(num_pools):
        my_size = len(pools[ppi])
        for ppj in range(num_pools):
            other_size = len(pools[ppj])
            pool_matchup_count = int(my_size*other_size/2)
            if ppi==ppj:
                pool_matchup_count = int(my_size*(my_size-1)/2)
            total_count = int(matchups*pool_matchup_count)
            if not matchups_exact:
                games_remaining = total_games - ((matchups-1)*unique_games)
                # print(total_games,matchups,unique_games,games_remaining,pool_matchup_count,(pool_matchup_count/unique_games))
                # print(total_count,'becomes...')
                total_count = int((matchups-1)*pool_matchup_count + (games_remaining*pool_matchup_count//unique_games))
                # print(total_count)
            if ppi == ppj:
                model.Add(sum(pool_balance[ppi][ppj]) >= total_count)
                model.Add(sum(pool_balance[ppi][ppj]) <= total_count+1)
            else:
                # hard equality generally works okay here
                # now that I'm figuring the count properly
                model.Add(sum(pool_balance[ppi][ppj]) == total_count)
                #  model.Add(sum(pool_balance[ppi][ppj]) <= local_count+1)

def add_one_game_per_day(matchdays,matches_per_day,teams,fixtures,model):
    # loop to list possible opponents for each team
    # each day, team t plays either home or away, but only once
    # or later, once becomes matches_per_day?
    for d in matchdays:
        for t in teams:
            possible_opponents=[]
            for opponent in teams:
                if t == opponent:
                    continue
                # t is home possibility
                possible_opponents.append(fixtures[d][t][opponent])
                # t is away possibility
                possible_opponents.append(fixtures[d][opponent][t])
            model.Add(sum(possible_opponents) == 1) # can only play one game per day

def add_one_matchup_per_round_robin(teams,fixtures,model,matchups,matchups_exact,unique_games,matches_per_day,num_matchdays):
    days_to_play = int(unique_games // matches_per_day)
    # print('unique_games',unique_games,
    #       '\nnum matches per day',matches_per_day,
    #       '\ndays to play',days_to_play,
    #       '\ntotal games possible',total_games)
    for t in teams:
        # I think I can reduce constraints by using the next loop
        # for opponent in range(t+1,num_teams):
        # but for first pass, keep with the one from C++ code
        for opponent in teams:
            if t == opponent:
                continue
            prior_home = []
            for m in range(matchups):
                current_home = []
                pairings = []
                # if m = matchups - 1, then last time through
                days = int(days_to_play)
                if m == matchups - 1:
                    days = int(min(days_to_play,num_matchdays - m*days_to_play))
                # print('days',days)
                for d in range(days):
                    theday = int(d + m*days_to_play)
                    # print('theday',theday)
                    pairings.append(fixtures[theday][t][opponent])
                    pairings.append(fixtures[theday][opponent][t])
                    # current_home.append(fixtures[theday][t][opponent])
                if m == matchups-1 and not matchups_exact:
                    # print('last matchup',m,'relaxed pairings constraint')
                    model.Add(sum(pairings) <= 1)
                else:
                    # print('matchup',m,'hard pairings constraint')
                    model.Add(sum(pairings) == 1)
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

def add_breaks_constraint(teams,at_home,num_matchdays,model):
    breaks = []
    for t in teams:
        for d in range(num_matchdays-1):
            breaks.append(model.NewBoolVar('two home or two away for team %i, starting on matchday %i' % (t,d)))

            model.AddBoolOr([at_home[d][t],at_home[d+1][t],breaks[-1]])
            model.AddBoolOr([at_home[d][t].Not(),at_home[d+1][t].Not(),breaks[-1]])

            model.AddBoolOr([at_home[d][t].Not(),at_home[d+1][t],breaks[-1].Not()])
            model.AddBoolOr([at_home[d][t],at_home[d+1][t].Not(),breaks[-1].Not()])

            # I couldn't figure this out, so I wrote a little program
            # and proved it.  These effectively are identical to
            #
            # model.Add(at_home[d][t] == at_home[d+1][t]).OnlyEnforceIf(breaks[-1])
            # model.Add(at_home[d][t] != at_home[d+1][t]).OnlyEnforceIf(breaks[-1].Not())
            #
            # except they are a little more efficient, I believe.  Wrote it up in a blog post

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

def daily_fixtures(model, num_teams, num_days):
    home_fix = partial(home_fixtures,model=model,num_teams=num_teams)
    result = list(map(lambda x: home_fix(day=x), list(range(num_days))))
    return result


def create_at_home_array(model,num_teams,day):
    name_prefix = 'at_home: day %i, ' % day
    return [ model.NewBoolVar(name_prefix+'home %i' % home) for home in range(num_teams) ]


def daily_at_home(model, num_teams, num_days):
    home_fix = partial(create_at_home_array,model=model,num_teams=num_teams)
    result = list(map(lambda x: home_fix(day=x), list(range(num_days))))
    return result


def model_matches(num_teams,
                  num_matchdays,
                  num_matches_per_day,
                  num_pools,
                  max_home_stand
):

    model = cp_model.CpModel()

    print('num_teams',          num_teams,
          'num_matchdays',      num_matchdays,
          'num_matches_per_day',num_matches_per_day,
          'num_pools',          num_pools,
          'max_home_stand',     max_home_stand)

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

    fixtures = [] # all possible games
    at_home = []  # whether or not a team plays at home on matchday
    all_home_games = [] # across all match days, home games for team

    pool_play = [] # play between pools, for team vs pool balancing
    pool_balance = [] # also play between pools, for pool vs pool
    # now for pool to pool, balance play
    # expected number is...um
    # number of pools cross number of pools divided into number of days to play
    pools = []
    pool_size = int(num_teams//num_pools)
    for g in range(num_pools):
        if g < num_pools-1:
            pools.append(list(range(int(g*pool_size),int((g+1)*pool_size))))
        else:
            # Last pool might need to be bigger.  If this ever gets used
            # in anger, the remainder should be spread over multiple
            # pools.
            pools.append(list(range(int(g*pool_size),num_teams)))

    fixtures = []
    at_home = []

    for d in matchdays:
        fixtures.append([])
        at_home.append([])
        for i in teams:
            fixtures[d].append([])
            home_pool = num_pools
            for j in teams:
                fixtures[d][i].append(model.NewBoolVar('fixture: home team %i, opponent %i, matchday %i' % (i,j,d)))
                if i == j:
                    model.Add(fixtures[d][i][j] == 0) # forbid playing self
            # is team i playing at home on day d?
            at_home[d].append(model.NewBoolVar('team %i is home on matchday %i' % (i,d)))

    # link at_home[day][team] in terms of fixtures
    #
    # Note this might have issues if byes are valid.  In that case, if
    # a team has a bye on a match day, it plays neither home nor away.
    # But at_home[d][t] == False implies away, when it might be a by
    # if the team t does not play that day
    for d in matchdays:
        for t in teams:
            for opponent in teams:
                if t == opponent:
                    continue
                model.AddImplication(fixtures[d][t][opponent], at_home[d][t])
                model.AddImplication(fixtures[d][t][opponent], at_home[d][opponent].Not())


    (pool_play,pool_balance) = collect_pool_play_fixtures(teams,pools,matchdays,fixtures)

    add_pool_play_constraints(pools,pool_play,model,matchups,matchups_exact,unique_games,total_games)

    add_pool_balance_constraints(pools,pool_balance,model,matchups,matchups_exact,unique_games,total_games)

    add_one_game_per_day(matchdays,num_matches_per_day,teams,fixtures,model)

    # each matchup between teams happens at most "matchups" times per season
    # want to add a constraint here to force alternating home and away for same team matchups
    # assert 0
    add_one_matchup_per_round_robin(teams,fixtures,model,matchups,matchups_exact,unique_games,num_matches_per_day,num_matchdays)


    add_max_home_stand_constraint(teams,at_home,model,num_matchdays,max_home_stand)

    breaks = add_breaks_constraint(teams,at_home,num_matchdays,model)


    # let the solver minimize the number of breaks required to make
    # the schedule work

    model.Minimize(sum(breaks))

    return (pools,fixtures,model)


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

def report_results(solver,status,fixtures,pools,num_teams,num_matchdays,time_limit=None,csv=None):

    if status == cp_model.INFEASIBLE:
        return status

    if status == cp_model.UNKNOWN:
        print('Not enough time allowed to compute a solution')
        print('Add more time using the --timelimit command line option')
        return status

    print('Optimal objective value: %i' % solver.ObjectiveValue())


    screen_dump_results(solver,fixtures,pools,num_teams,num_matchdays)

    if status != cp_model.OPTIMAL and solver.WallTime() >= time_limit:
        print('Please note that solver reached maximum time allowed %i.' % time_limit)
        print('A better solution than %i might be found by adding more time using the --timelimit command line option'% solver.ObjectiveValue())


    if csv:
        csv_dump_results(solver,fixtures,pools,num_teams,num_matchdays,csv)


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

    args = parser.parse_args()

    # set default for num_matchdays
    num_matches_per_day = args.num_matches_per_day
    if not num_matches_per_day:
        num_matches_per_day = args.num_teams // 2


    ncpu = len(os.sched_getaffinity(0))
    cpu = args.cpu
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


    # assign_matches()
    (pools,fixtures,model) = model_matches(args.num_teams,
                   args.num_matchdays,
                   num_matches_per_day,
                   args.num_pools,
                   args.max_home_stand)

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


if __name__ == '__main__':
    main()
