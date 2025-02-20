#/bin/bash

export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/service-account-file.json"
./venv/bin/python bot.py