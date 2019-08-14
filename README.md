# Sports Scheduling using OR Tools

The genesis of this package was from a question on the OR Tools
forum.  In order to answer the question, I translated the C++ example
[sports_scheduling.cc](https://github.com/google/or-tools/blob/stable/examples/cpp/sports_scheduling_sat.cc)
into Python.  I am going to submit this translation back to the
project as an example, but I didn't feel comfortable doing so until I
set up some tests to make sure that my code wasn't buggy.

So I created this package primarily to be able to include tests, and
then I decided I may as well push it up to github in case anyone else
is interested in using the code, and in order to maintain it.

# Using OR Tools in a Docker Container

My approach to OR Tools is to use it within a Docker container.  This
works for me.

This project's Docker image can be built using the project's Dockerfile.  To do this, change into the
Docker directory and execute the build command:

```
cd Docker
docker build -t jmarca/ortools_python
```

This will build an image based on the official Python Docker image
that includes the latest version of OR Tools [version 7.3 at this
time](https://github.com/google/or-tools/releases/tag/v7.3).

To use the solver in this image, you have to create a container and
tell it how to find your data and code.  From the root of this
project, you can do this:

```
docker run -it \
           --rm \
	       -v /etc/localtime:/etc/localtime:ro \
           --name sports_scheduling \
           -v ${PWD}:/work \
           -w /work \
           jmarca/ortools_python bash
```

This will create a container and link the current working directory
(`${PWD}`) to the `/work` directory inside of the container.  From
within the container, you can then run all the commands you would
expect from the bash command line prompt.

If you want to run code in the container but *not* spawn a bash
prompt, you can do something like this, assuming you have code in
`src` and data in `data` directories:


```
docker run -it \
           --rm \
	       -v /etc/localtime:/etc/localtime:ro \
           --name sports_scheduling \
           -v ${PWD}:/work \
           -w /work \
           jmarca/ortools_python python src/runme.py --various --commandline --options
```

# Non-Docker setup

If you do not have Docker, then you can install all of the
dependencies using pip.

## Linux

I run linux, and I've tested installing OR tools with this line

```
python -m pip install -U --user ortools
```

## Non-Linux

For non-linux platforms, the approach is the same.  See
https://developers.google.com/optimization/install/python/ for
details.  For example, on windows assuming you have python 3.7
installed, from a command line prompt you can run:

```
python -m pip install --user ortools
```

## Conda

Just guessing here, but if you're running conda, you'll need to
install pip first.  See https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-pkgs.html?highlight=pip#installing-non-conda-packages

For example, something like (untested)
```
conda install pip
pip install ortools
```

# Running the Scheduler

There is just one executable at this time:
`src/sports_schedule_sat.py`

```
 --help
usage: sports_schedule_sat.py [-h] -t,--teams NUM_TEAMS -d,--days
                              NUM_MATCHDAYS
                              [--matches_per_day NUM_MATCHES_PER_DAY]
                              [-p,--pools NUM_POOLS] [--csv CSV]
                              [--timelimit TIME_LIMIT] [--cpu CPU] [--debug]
                              [--max_home_stand MAX_HOME_STAND]

Solve sports league match play assignment problem

optional arguments:
  -h, --help            show this help message and exit
  -t,--teams NUM_TEAMS  Number of teams in the league
  -d,--days NUM_MATCHDAYS
                        Number of days on which matches are played. Default is
                        enough days such that every team can play every other
                        team, or (number of teams - 1)
  --matches_per_day NUM_MATCHES_PER_DAY
                        Number of matches played per day. Default is number of
                        teams divided by 2. If greater than the number of
                        teams, then this implies some teams will play each
                        other more than once. In that case, home and away
                        should alternate between the teams in repeated
                        matchups.
  -p,--pools NUM_POOLS  How many separate pools should the teams be separated
                        into. Default is 1
  --csv CSV             A file to dump the team assignments. Default is
                        output.csv
  --timelimit TIME_LIMIT
                        Maximum run time for solver, in seconds. Default is 60
                        seconds.
  --cpu CPU             Number of workers (CPUs) to use for solver. Default is
                        6 or number of CPUs available, whichever is lower
  --debug               Turn on some print statements.
  --max_home_stand MAX_HOME_STAND
                        Maximum consecutive home or away games. Default to 2,
                        which means three home or away games in a row is
                        forbidden.
```


# Tests

Tests are run with pytest.

```
pytest --cov=src
```
