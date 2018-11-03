#!/bin/bash

# bash wrappers for docker run commands
# should work on linux, perhaps on OSX


#
# Environment vars
#

# for OSRM, what version, what data to run

# OSRM_IMAGE_VERSION=${OSRM_IMAGE_VERSION:-2018-07-09T16-00-17} #greater chicago version, w/ Indiana
# OSRM_IMAGE_VERSION=$(docker image ls | grep osrm-preloaded-backend | awk '{print $2}')
# OSRM_IMAGE_VERSION=${OSRM_IMAGE_VERSION:-2018-06-05T14-01-17} #greater portland version
OSRM_IMAGE_VERSION=${OSRM_IMAGE_VERSION:-2018-07-09T16-00-17} #greater chicago
OSRM_DATA=${OSRM_DATA:-/data/north-america/us/greater-chicago.osrm}
# OSRM_DATA=${OSRM_DATA:-/data/north-america/us/greater-portland.osrm}

# # useful for connecting GUI to container
# SOCK=/tmp/.X11-unix
# XAUTH=/tmp/.docker.xauth
# xauth nlist $DISPLAY | sed -e 's/^..../ffff/' | xauth -f $XAUTH nmerge -
# chmod 755 $XAUTH

#
# Helper Functions
#
dcleanup(){
	local containers
	mapfile -t containers < <(docker ps -aq 2>/dev/null)
	docker rm "${containers[@]}" 2>/dev/null
	local volumes
	mapfile -t volumes < <(docker ps --filter status=exited -q 2>/dev/null)
	docker rm -v "${volumes[@]}" 2>/dev/null
	local images
	mapfile -t images < <(docker images --filter dangling=true -q 2>/dev/null)
	docker rmi "${images[@]}" 2>/dev/null
}
del_stopped(){
	local name=$1
	local state
	state=$(docker inspect --format "{{.State.Running}}" "$name" 2>/dev/null)

	if [[ "$state" == "false" ]]; then
		docker rm "$name"
	fi
}
relies_on(){
	for container in "$@"; do
		local state
		state=$(docker inspect --format "{{.State.Running}}" "$container" 2>/dev/null)

		if [[ "$state" == "false" ]] || [[ "$state" == "" ]]; then
			echo "$container is not running, starting it for you."
			$container
		fi
	done
}

relies_on_network(){
    for network in "$@"; do
        local state
        state=$(docker network inspect --format "{{.Created}}" "$network" 2>/dev/null)

        if [[ "$state" == "false" ]] || [[ "$state" == "" ]]; then
            echo "$network is not up, starting it for you."
            $network
        fi
    done
}

routing_nw(){
    # create the network for communicating
    docker network create --driver bridge routing_nw
}

osrm_routed(){
    relies_on_network routing_nw

    docker run -d --rm \
           -v /etc/localtime:/etc/localtime:ro \
           --network=routing_nw \
           --name osrm_routed \
           jmarca/osrm-preloaded-backend:${OSRM_IMAGE_VERSION} \
           osrm-routed --algorithm mld ${OSRM_DATA}
}

osrm_frontend(){
    relies_on_network routing_nw

    # to get this to work in the browser, you have to have the correct
    # network below.  So if docker isn't assigning the ip address
    # 172.18.0.2 to the osrm backend, change the ip below.  I need to
    # write a little command line script to grab it from the docker
    # network command, but I haven't done that yet.
    #
    # originally I put -e OSRM_BACKEND='http://osrm_routed:5000' here,
    # but that doesn't work on the browser, which is where this is
    # actually triggered.
    docker run -d --rm \
		       -v /etc/localtime:/etc/localtime:ro \
           -e OSRM_BACKEND='http://172.19.0.2:5000' \
           --network=routing_nw \
           --name osrm_frontend \
           -p 9966:9966 \
           osrm/osrm-frontend
}

python_environment(){
    # relies_on osrm_routed osrm_frontend

    docker run -it \
           --rm \
           --user 1000 \
	   -v /etc/localtime:/etc/localtime:ro \
	   -v /tmp/.X11-unix:/tmp/.X11-unix \
	   -e "DISPLAY=unix${DISPLAY}" \
           --network=routing_nw \
           --name ortools_python \
           -v ${PWD}:/home/user \
           jmarca/ortools_python bash
}

# osrm_routed
# route_optimization_service
