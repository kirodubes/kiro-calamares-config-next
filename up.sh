#!/bin/bash
set -eo pipefail
##################################################################################################################
# Author    : Erik Dubois
# Website   : https://www.erikdubois.be
# Youtube   : https://youtube.com/erikdubois
# Github    : https://github.com/erikdubois
# Github    : https://github.com/kirodubes
# Github    : https://github.com/buildra
# SF        : https://sourceforge.net/projects/kiro/files/
##################################################################################################################
#
#   DO NOT JUST RUN THIS. EXAMINE AND JUDGE. RUN AT YOUR OWN RISK.
#
##################################################################################################################
#tput setaf 0 = black
#tput setaf 1 = red
#tput setaf 2 = green
#tput setaf 3 = yellow
#tput setaf 4 = dark blue
#tput setaf 5 = purple
#tput setaf 6 = cyan
#tput setaf 7 = gray
#tput setaf 8 = light blue
##################################################################################################################

# variables and functions
workdir=$(pwd)
dir="calamares-next-3.3.14.r39.g274996f"
source="/home/erik/KIRO/kiro-pkgbuild/"
destiny="/home/erik/KIRO/kiro-calamares-config-next/etc/calamares/pkgbuild/"

##################################################################################################################

rm -r /home/erik/KIRO/kiro-calamares-config-next/etc/calamares/pkgbuild/*
cp -r $source$dir/* $destiny

# Below command will backup everything inside the project folder
git add --all .

# Committing to the local repository with a message containing the time details and commit text

git commit -m "update"

# Push the local files to github

branch=$(git rev-parse --abbrev-ref HEAD)
git push -u origin "$branch"

echo
tput setaf 6
echo "##############################################################"
echo "###################  $(basename $0) done"
echo "##############################################################"
tput sgr0
echo
