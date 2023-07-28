#!/bin/sh
docker rmi "$(docker images -q --filter 'dangling=true')"