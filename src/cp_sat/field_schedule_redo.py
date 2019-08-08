import pandas as pd
import numpy as np

from ortools.sat.python import cp_model

# going to follow along with sports_scheduling_sat.cc from OR Tools
# sourcecode examples

def model(num_teams=32,
          num_matchdays=10,
          num_matches_per_day=16,
          num_groups=4):

    model = cp_model.CpModel()

    num_homegames = int(num_matchdays//2)
    home_hard_constraint = True
    if num_matchdays % 2:
        home_hard_constraint = False

    groups = []
    group_size = int(num_teams//num_groups)
    for g in range(num_groups):
        if g < num_groups-1:
            groups.append(list(range(int(g*group_size),int((g+1)*group_size))))
        else:
            groups.append(list(range(int(g*group_size),num_teams)))

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
            home_pool = num_groups
            for j in teams:
                fixtures[d][i].append(model.NewBoolVar('fixture: home team %i, opponent %i, matchday %i' % (i,j,d)))
                if i == j:
                    model.Add(fixtures[d][i][j] == 0) # forbid playing self
            # is team i playing at home on day d?
            at_home[d].append(model.NewBoolVar('team %i is home on matchday %i' % (i,d)))

    # balance home and away games
    for t in teams:
        all_home_games.append([])
        for d in matchdays:
            all_home_games[t] += fixtures[d][t]
        if home_hard_constraint:
            model.Add(sum(all_home_games) == num_homegames)
        else:
            # odd number of games, so might have one more or one less homegame
            model.Add(sum(all_home_games) >= num_homegames)
            model.Add(sum(all_home_games) <= num_homegames+1)

    # pool play loop
    # home team group is outer loop

    # prep the arrays
    for t in teams:
        pool_play.append([])
        for ppi in range(num_groups):
            pool_play[t].append([])

    for ppi in range(num_groups):
        pool_balance.append([])
        for ppj in range(num_groups):
            pool_balance[ppi].append([])


    for ppi in range(num_groups):
        for t in groups[ppi]:
            # other team group is inner loop
            for ppj in range(num_groups):
                # over all the days, have to play each pool at least once
                for d in matchdays:
                    for opponent in groups[ppj]:
                        if t == opponent:
                            # cannot play self
                            continue
                        # save case of t is home, playing vs pool j
                        pool_play[t][ppj].append(fixtures[d][t][opponent])
                        # save case of t is away, playing vs pool j
                        ## pool_play[t][ppj].append(fixtures[d][opponent][t])
                        # save pool home vs pool away case
                        pool_balance[ppi][ppj].append(fixtures[d][t][opponent])

    # pulling this out of the above loop for safety
    for t in teams:
        for ppi in range(num_groups):
            # over all the days, have to play each pool at least once
            # model.AddBoolOr(pool_play[t][ppj])
            # in order to require more than one, use Add(sum(...))
            model.Add(sum(pool_play[t][ppi]) >= 1)
    # now for group to group, balance play
    # 10 is hardcoded for now
    for ppi in range(num_groups):
        for ppj in range(num_groups):
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
        for d in range(num_matchdays - 2):
            model.AddBoolOr([at_home[d][t],
                             at_home[d+1][t],
                             at_home[d+2][t]])
            model.AddBoolOr([at_home[d][t].Not(),
                             at_home[d+1][t].Not(),
                             at_home[d+2][t].Not()])



    # objective using breaks concept
    breaks = []
    for t in teams:
        for d in range(num_matchdays-1):
            breaks.append(model.NewBoolVar('two home or two away for team %i, starting on matchday %i' % (t,d)))
            # not sure what the point of these constraints are

            # at least one of at_home[d][t], at_home[d+1][t], or breaks[-1] is true
            # if break is false, then one or both of [home d, home d+1] must be true
            # if break is true, then one of both of [home d, home d+1] can be false
            model.AddBoolOr([at_home[d][t],at_home[d+1][t],breaks[-1]])
            #
            # assuming "away" means at_home[][].Not(), then
            #
            # at least one of away[d][t], away[d+1][t], or breaks[-1] is true
            # if break is false, then one or both of [away d, away d+1] must be true
            # if break is true, then one of both of [away d, away d+1] can be false
            model.AddBoolOr([at_home[d][t].Not(),at_home[d+1][t].Not(),breaks[-1]])
            # if break is false, then at least one of
            model.AddBoolOr([at_home[d][t].Not(),at_home[d+1][t],breaks[-1].Not()])
            model.AddBoolOr([at_home[d][t],at_home[d+1][t].Not(),breaks[-1].Not()])
    # constrain breaks
    model.Add(sum(breaks) >= 2*num_teams - 4)
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
    for i in range(num_groups):
        pool_vs_pool.append([0 for j in range(num_groups)])
        for t in groups[i]:
            team_pool_play.append([])
            for j in range(num_groups):
                for other in groups[j]:
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
        for i in range(num_groups):
            for t in groups[i]:
                for j in range(num_groups):
                    for other in groups[j]:
                        home = solver.Value(fixtures[d][t][other])
                        away = solver.Value(fixtures[d][other][t])
                        if home:
                            team_pool_play[t][j] += 1
                            pools[i][j] += 1
                        if away:
                            # t is away, but still playing vs pool j
                            team_pool_play[t][j] += 1


    all_combinations_sum = 0
    for i in range(num_groups):
        for j in range(num_groups):
            print('pool % at home vs pool % away, count = %'%(i,j,pool_vs_pool[i][j]))
            all_combinations_sum += pool_vs_pool[i][j]
    print('all combinations sum to',all_combinations_sum)

    for i in range(num_groups):
        for t in groups[i]:
            for j in range(num_groups):
                print('team %i versus pool %i = %i' % (t+1,j,team_pool_play[t][j]))

if __name__ == '__main__':
    model()
