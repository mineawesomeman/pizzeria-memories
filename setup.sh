#/bin/bash

echo Installing Required Libraries
sudo apt install pip
sudo apt install python3.11-venv

echo Setting up Python Enviroment
# create python enviroment
python3 -m venv ./venv
# install libraries
./venv/bin/pip install -r requirements.txt

echo Unpacking Messages
tar -xf messages.tar.gz