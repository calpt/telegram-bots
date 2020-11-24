#!/bin/bash
cd $( dirname "${BASH_SOURCE[0]}" )
chmod 755 init/mensabot
cp init/* /etc/init.d
sudo update-rc.d mensabot defaults
