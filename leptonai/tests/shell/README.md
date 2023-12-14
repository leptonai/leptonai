This is a simple class that uses the `/run` api to run a shell command on the
local deployment. Note: since the deployments are considered stateless, any
command you run that may have a non-ephemeral effect, such as creating a file
or so, will not be persistent, unless it is written to a persistent storage
such as the Lepton storage or a mounted S3.

To build the photon, do:

    lep photon create -n shell -m shell.py:Shell

To run the photon, simply do

    lep photon run -n shell [optional arguments]

