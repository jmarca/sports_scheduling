import argparse

from ortools.sat.python import cp_model

# going to follow along with sports_scheduling_sat.cc from OR Tools
# sourcecode examples

def model(num_teams=32,
          num_matchdays=10,
          num_matches_per_day=16,
          num_pools=4,
          max_home_stand=2,
          timelimit=None,
          cpu=None,
          csv=None,
          debug=None
):

    model = cp_model.CpModel()

    num_homegames = int(num_matchdays//2)
    home_hard_constraint = True
    if num_matchdays % 2:
        home_hard_constraint = False

    pools = []
    pool_size = int(num_teams//num_pools)
    for g in range(num_pools):
        if g < num_pools-1:
            pools.append(list(range(int(g*pool_size),int((g+1)*pool_size))))
        else:
            pools.append(list(range(int(g*pool_size),num_teams)))

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
        matchups = total_games // unique_games



    fixtures = [] # all possible games
    at_home = []  # whether or not a team plays at home on matchday
    all_home_games = [] # across all match days, home games for team
    pool_play = [] # play between pools, for team vs pool balancing
    pool_balance = [] # also play between pools, for pool vs pool

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

    # balance home and away games?  I think this is redundant with the
    # "breaks" constraints, later.
    # for t in teams:
    #     all_home_games.append([])
    #     for d in matchdays:
    #         all_home_games[t] += fixtures[d][t]

    #     if home_hard_constraint:
    #         model.Add(sum(all_home_games[t]) == num_homegames)
    #     else:
    #         # odd number of games, so might have one more or one less homegame
    #         model.Add(sum(all_home_games[t]) >= num_homegames)
    #         model.Add(sum(all_home_games[t]) <= num_homegames+1)

    # pool play loop
    # home team pool is outer loop

    # prep the arrays
    for t in teams:
        pool_play.append([])
        for ppi in range(num_pools):
            pool_play[t].append([])

    for ppi in range(num_pools):
        pool_balance.append([])
        for ppj in range(num_pools):
            pool_balance[ppi].append([])


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

    # pulling this out of the above loop for safety
    for t in teams:
        for ppi in range(num_pools):
            # over all the days, have to play each pool at least once
            # model.AddBoolOr(pool_play[t][ppj])
            # in order to require more than one, use Add(sum(...))
            model.Add(sum(pool_play[t][ppi]) >= 2)
    # now for pool to pool, balance play
    # 10 is hardcoded for now
    for ppi in range(num_pools):
        for ppj in range(num_pools):
            model.Add(sum(pool_balance[ppi][ppj]) == 10)

    # for this loop list possible opponents
    # each day, team t plays either home or away, but only once
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

    # each matchup between teams happens at most "matchups" times per season
    days_to_play = unique_games // num_matches_per_day
    for t in teams:
        # I think I can reduce constraints by using the next loop
        # for opponent in range(t+1,num_teams):
        # but for first pass, keep with the one from C++ code
        for opponent in teams:
            if t == opponent:
                continue

            for m in range(matchups):
                pairings = []
                # if m = matchups - 1, then last time through
                days = int(days_to_play)
                if m == matchups - 1:
                    days = int(min(days_to_play,num_matchdays - m*days_to_play))
                for d in range(days):
                    theday = int(d + m*days_to_play)
                    pairings.append(fixtures[theday][t][opponent])
                    pairings.append(fixtures[theday][opponent][t])
                if m == matchups-1 and not matchups_exact:
                    model.Add(sum(pairings) <= 1)
                else:
                    model.Add(sum(pairings) == 1)

    # maintain at_home[day][team]
    for d in matchdays:
        for t in teams:
            for opponent in teams:
                if t == opponent:
                    continue
                model.AddImplication(fixtures[d][t][opponent], at_home[d][t])
                model.AddImplication(fixtures[d][t][opponent], at_home[d][opponent].Not())

    # balance home and away games?


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

    # objective using breaks concept
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



    # constrain breaks
    model.Add(sum(breaks) >= num_matchdays)
    model.Minimize(sum(breaks))
    # run the solver
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10800 # three hours.  Only takes about 90 minutes or so
    solver.parameters.log_search_progress = True
    solver.parameters.num_search_workers = 6 # oh my god that really speeds things up!

    # solution_printer = SolutionPrinter() # since we stop at first
    # solution, this isn't really
    # necessary I think
    status = solver.Solve(model)
    print('Solve status: %s' % solver.StatusName(status))
    print('Optimal objective value: %i' % solver.ObjectiveValue())
    print('Statistics')
    print('  - conflicts : %i' % solver.NumConflicts())
    print('  - branches  : %i' % solver.NumBranches())
    print('  - wall time : %f s' % solver.WallTime())

    if status == cp_model.INFEASIBLE:
        return status

    # these should sum to 10 each
    pool_vs_pool = []
    # these should be balanced
    team_pool_play=[]
    for i in range(num_pools):
        pool_vs_pool.append([0 for j in range(num_pools)])
        for t in pools[i]:
            team_pool_play.append([])
            for j in range(num_pools):
                for other in pools[j]:
                    team_pool_play[t].append(0)



    for d in matchdays:
        game = 0
        for t in teams:
            for other in teams:
                home = solver.Value(fixtures[d][t][other])
                if home:
                    game += 1
                    print('day %i game %i home %i away %i' %(d+1,game,t+1,other+1))

    for d in matchdays:
        for i in range(num_pools):
            for t in pools[i]:
                for j in range(num_pools):
                    for other in pools[j]:
                        home = solver.Value(fixtures[d][t][other])
                        away = solver.Value(fixtures[d][other][t])
                        if home:
                            team_pool_play[t][j] += 1
                            pool_vs_pool[i][j] += 1
                        if away:
                            # t is away, but still playing vs pool j
                            team_pool_play[t][j] += 1


    all_combinations_sum = 0
    for i in range(num_pools):
        for j in range(num_pools):
            print('pool %i at home vs pool %i away, count = %i'%(i,j,pool_vs_pool[i][j]))
            all_combinations_sum += pool_vs_pool[i][j]
    print('all combinations sum to',all_combinations_sum)

    for i in range(num_pools):
        for t in pools[i]:
            for j in range(num_pools):
                print('team %i versus pool %i = %i' % (t+1,j,team_pool_play[t][j]))

    # print break results, to get a clue what they are doing
    print('Breaks')
    for b in breaks:
        print('  %s is %i' % (b.Name(), solver.Value(b)))

def main():
    """Entry point of the program."""
    parser = argparse.ArgumentParser(description='Solve sports league match play assignment problem')
    parser.add_argument('-t,--teams', type=int, dest='num_teams',
                        help='Number of teams in the league')

    parser.add_argument('-d,--days', type=int, dest='num_matchdays',
                        help='Number of days on which matches are played.  Default is enough days such that every team can play every other team, or (number of teams - 1)')

    parser.add_argument('--matches_per_day', type=int, dest='num_matches_per_day',
                        help='Number of matches played per day.  Default is number of teams divided by 2.  If greater than the number of teams, then this implies some teams will play each other more than once.  In that case, home and away should alternate between the teams in repeated matchups.')

    parser.add_argument('-p,--pools', type=int, dest='num_pools',default=4,
                        help='CSV file for dumping output for demand details (including invalid demands, etc)')

    parser.add_argument('--csv', type=str, dest='csv_file', default='output.csv',
                        help='A file to dump the team assignments.  Default is output.csv')

    parser.add_argument('--timelimit', type=int, dest='timelimit', default=10,
                        help='Maximum run time for solver, in minutes.  Default is 10 minutes.')
    parser.add_argument('--cpu',type=int,dest='cpu',default=6,
                        help='Number of CPUs to use for solver.  Default is 6')

    parser.add_argument('--debug', type=bool, dest='debug', default=False,
                        help="Turn on some print statements.")

    parser.add_argument('--max_home_stand',type=int,dest='max_home_stand',default=2,
                        help="Maximum consecutive home or away games.  Default to 2, which means three home or away games in a row is forbidden.")

    args = parser.parse_args()

    # set default for num_matchdays
    num_matches_per_day = args.num_matches_per_day
    if not num_matches_per_day:
        num_matches_per_day = args.num_teams - 1


    model()

if __name__ == '__main__':
    main()
