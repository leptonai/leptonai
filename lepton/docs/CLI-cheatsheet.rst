Cheatsheet
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
   lepton photon push -n bar-py -r http://k8s-default-leptonse-42c1558c73-673051545.us-east-1.elb.amazonaws.com

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
