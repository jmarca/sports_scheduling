# sample run command:
# docker run -it -v /tmp/.X11-unix:/tmp/.X11-unix -e "DISPLAY=unix:0" -v /home/james:/work/output jmarca/route_optimization_service bash
#
# build this with
# docker build -t jmarca/route_optimization_service .
#

FROM python:3.7

COPY requirements.txt ./
RUN pip install --upgrade pip && \
   pip install --upgrade --no-cache-dir -r requirements.txt


# test the install
RUN python -c "from ortools.linear_solver import pywraplp"

ENV HOME /work
RUN useradd --create-home --home-dir $HOME user \
	&& chown -R user:user $HOME
ENV LANG C.UTF-8
USER user

WORKDIR $HOME
