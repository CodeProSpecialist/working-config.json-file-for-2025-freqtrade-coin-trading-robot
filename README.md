# working-config.json-file-for-2025-freqtrade-coin-trading-robot
working config.json file for freqtrade 2025 version. 

Below is for freqtrade whitelist coin list that is generated from a python program to get profitable coins to buy

use this command to run freqtrade on the command line with any strategy:

freqtrade trade --userdir ~/freqtrade_data/user_data --config ~/freqtrade_data/config.json --strategy Bandtastic

---------------------
# Coin List Writer
First get a Krakin API Key and secret key from their website. 

Utulize the following python script to automatically make a profitable coin list every 24 hours. 
Place the python script in your 
home folder, in the directory named 
freqtrade-whitelist. 

cd ~/

mkdir freqtrade-whitelist

cd freqtrade-whitelist

python3 profit-coin-list-writer.py

----------------
In Linux, copy the following to 
the bottom of ~/.bashrc



export FREQTRADE__EXCHANGE__PAIR_WHITELIST=$(cat ~/freqtrade-whitelist/whitelist.json)
