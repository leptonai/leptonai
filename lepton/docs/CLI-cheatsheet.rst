CLI Cheatsheet
=============

Create Photon

.. code:: shell

   lepton photon create -n gpt2 -m hf:gpt2 
   lepton photon create -n some-python -m py:./some-counter.py:Counter



Run Photon

.. code:: shell
   
   lepton photon run --name gpt --model hf:gpt2
   lepton photon run --name bar-py --model py:./some-counter.py:Counter
   lepton photon run -i e64d943ec7b0ce12d06a1f728b962610 -r http://k8s-default-leptonse-42c1558c73-673051545.us-east-1.elb.amazonaws.com

Push Photon

.. code:: shell
   
   lepton photon push -n some-foo-bar -r http://k8s-default-leptonse-42c1558c73-673051545.us-east-1.elb.amazonaws.com
   lepton photon push -n Earning_Call_with_image -r http://k8s-default-leptontf-2dfefce868-1895553700.us-east-1.elb.amazonaws.com


Fetch Photon

.. code:: shell
   
   lepton photon fetch -i e64d943ec7b0ce12d06a1f728b962610 -r http://k8s-default-leptonse-42c1558c73-673051545.us-east-1.elb.amazonaws.com

List Photon

.. code:: shell
   
   # List photons on remote
   lepton photon list -r http://k8s-default-leptonse-42c1558c73-673051545.us-east-1.elb.amazonaws.com
   # List photons on local
   lepton photon list

Remove Photon

.. code:: shell
   
   lepton photon remove -n some-foo-bar
   lepton photon remove -i e64d943ec7b0ce12d06a1f728b962610 -r http://k8s-default-leptonse-42c1558c73-673051545.us-east-1.elb.amazonaws.com

Write docs

.. code:: shell
   
   cd lepton/docs
   pip install -r requirements.txt
   make html

   cd lepton/docs/_build
   http-server

Then go visit localhost: http://127.0.0.1:8080/html/

Remote mode usage

.. code:: shell

   # List remotes
   lepton remote list
   # Switch to remote cluster via url
   lepton remote login -r https://dev-staging.cloud.lepton.ai/api/v1
   # Switch to remote cluster via name
   lepton remote login -n staging
   # Push photon to remote from local
   lepton photon push -n {PHOTON_NAME}
  

Setup for creating photon from Github
=====================================

Step 1: Generate a token
------------------------
Go to `Github Personal Access Tokens Page <https://github.com/settings/tokens?type=beta>`_, click **Generate new token**. Make the following changes based on your requirements:

- Resource Owner: Change it to the owner of the repo from which you will be creating the photon.
- Repository access: For security purposes, only select the repo you'd like to be used.
- Permissions:
    - Contents: Give read-only permission.

Then click **Generate token**.

Step 2: Set up the environment variable for CLI to pull the repo
----------------------------------------------------------------
In the terminal, type in the following commands:

.. code-block:: bash

   export GITHUB_USER={YOUR_GITHUB_USERNAME}
   export GITHUB_TOKEN={THE_TOKEN_GENERATED_FROM_STEP_1}

Step 3: Create photon via lepton cli
------------------------------------

.. code-block:: bash

   lepton photon create -n {PHOTON_NAME} -m py:{GIT_REPO_URL}:{PATH_TO_SCRIPT}:{CLASS_NAME}


+----------------+------------------------------------------------------+---------------------------------------------+
| Key            | Description                                          | Example                                     |
+================+======================================================+=============================================+
| PHOTON_NAME    | The name of the photon                               | my-fs-counter                               |
+----------------+------------------------------------------------------+---------------------------------------------+
| GIT_REPO_URL   | The url for the repo                                 | github.com/leptonai/examples.git            |
+----------------+------------------------------------------------------+---------------------------------------------+
| PATH_TO_SCRIPT | The file extends the runner class                    | Counter_with_file_and_dependency/counter.py |
+----------------+------------------------------------------------------+---------------------------------------------+
| CLASS_NAME     | The class extends the runner class inside the script | Counter                                     |
+----------------+------------------------------------------------------+---------------------------------------------+
