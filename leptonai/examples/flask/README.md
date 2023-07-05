This is a simple class that demonstrates how to use Lepton to to run an existing flask application.

First build a python package for the existing flask app, run

    pip wheel ./flask_app

which generates a .whl file for the flask_app package.

Then to create the photon, do:

    lep photon create -n flask-app -m photon.py:FlaskPhoton

To run the photon, do

    lep photon run -n flask-app

To test the service, (in another terminal) do

    curl http://0.0.0.0:8080

You should see responses ("Hello from Flask!") from the flask app.
