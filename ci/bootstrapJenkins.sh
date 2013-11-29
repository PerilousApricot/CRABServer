#!/bin/bash
# Static script to get our needed repositories with the proper revisions as
# well as an RPM checkout for the needed dependencies

echo "Beginning bootstrapJenkins.sh at $(date)"
ARCH="slc5_amd64_gcc461"
TARGET="./repos"
CRABSERVERREF="htcondor_poc"
CRABCLIENTREF="htcondor_poc"
WMCOREREF="master"
CRABSERVERREPO="https://github.com/dmwm/CRABServer.git"
CRABCLIENTREPO="https://github.com/dmwm/CRABClient.git"
WMCOREREPO="https://github.com/dmwm/WMCore.git"
ENABLECRABSERVER=0
ENABLECRABCLIENT=0
ENABLEWMCORE=0
RPMSREQUESTED_SLC5="cms+wmcore-devtools+1.1-comp8 cms+crabserver+3.3.0.rc5 cms+crabtaskworker+3.3.0.rc5-comp cms+crabclient+3.3.0.pre3"
RPMSREQUESTED_SLC6=""
RPMSREQUESTED="$RPMSREQUESTED_SLC5"
CMSREP_HOST="cmsrep.cern.ch"
CMSREP_REPO="comp.pre"

while [[ $# > 1 ]]; do
    key="$1"
    shift
        case $key in
        --target) TARGET="$1" ; shift ;;
        --crabServerRef) [ ! -z "$1" ] && CRABSERVERREF="$1"; ENABLECRABSERVER=1; shift ;;
        --crabClientRef)  [ ! -z "$1" ] && CRABCLIENTREF="$1"; ENABELCRABCLIENT=1; shift ;;
        --wmCoreRef)  [ ! -z "$1" ] && WMCOREREF="$1"; ENABLEWMCORE=1; shift ;;
        --crabServerRepo)  [ ! -z "$1" ] && CRABSERVERREPO="$1"; ENABLECRABSERVER=1; shift ;;
        --crabClientRepo)  [ ! -z "$1" ] && CRABCLIENTREPO="$1"; ENABLECRABCLIENT=1; shift ;;
        --wmCoreRepo)  [ ! -z "$1" ] && WMCOREREPO="$1"; ENABLEWMCORE=1; shift ;;
        *)
            echo "Got an unknown option ${key}"
        ;;
    esac
done

if [ ! -d $TARGET ]; then
    mkdir -p $TARGET
fi

DEPS_PATH="/tmp/crab3-testing-deps-$(whoami)"
REPO_KEY="$CMSREP_HOST $CMSREP_REPO $RPMSREQUESTED"
OLD_KEY=""
if [ -e "$DEPS_PATH/install_key" ]; then
    OLD_KEY=$(cat ${DEPS_PATH}/install_key)  
fi
if [ "$REPO_KEY" != "$OLD_KEY" ]; then
    echo "Dependencies requested don't match, reinstalling"
    # get the dependencies
    rm -rf $DEPS_PATH
    mkdir -p $DEPS_PATH
    wget -O $DEPS_PATH/bootstrap.sh http://$CMSREP_HOST/cmssw/$CMSREP_REPO/bootstrap.sh
    sh -e $DEPS_PATH/bootstrap.sh -architecture $ARCH -repository $CMSREP_REPO -server $CMSREP_HOST -path $DEPS_PATH setup
    (
        source $DEPS_PATH/$ARCH/external/apt/*/etc/profile.d/init.sh
        apt-get install -y $RPMSREQUESTED
        if [ $? -ne 0 ]; then
            echo "ERROR: Couldn't install RPMS"
            exit 1
        fi
    )
    printf "$REPO_KEY" > $DEPS_PATH/install_key
fi

function checkBare {
    BAREPATH="/tmp/$(whoami)-$1-baregitDMWM"
    if [ ! -d $BAREPATH ]; then
        echo "Downloading bare repository for $1"
        git clone --bare $2 $BAREPATH
    fi
}

function getRepo {
    echo "Checking out $3"
    BAREPATH="/tmp/$(whoami)-$4-baregitDMWM"
    set -x
    git clone --reference="$BAREPATH" $1 $2
    cd $2
    git checkout $3
    cd -
    set +x
}

if [ $ENABLECRABSERVER -eq 1 ]; then
    checkBare CRABServer $CRABSERVERREPO
    getRepo $CRABSERVERREPO $TARGET/CRABServer $CRABSERVERREF CRABServer
fi
if [ $ENABLECRABCLIENT -eq 1 ]; then
    checkBare CRABClient $CRABCLIENTREPO
    getRepo $CRABCLIENTREPO $TARGET/CRABClient $CRABCLIENTREF CRABClient
fi
if [ $ENABLEWMCORE -eq 1 ]; then
    checkBare WMCore $WMCOREREPO
    getRepo $WMCOREREPO $TARGET/WMCore $WMCOREREF WMCore
fi
echo "Sourcing subsystems..."
for SUBSYSTEM in crabclient crabserver crabtaskworker wmcore-devtools; do
    echo "    ... $SUBSYSTEM"
    source $DEPS_PATH/$ARCH/cms/$SUBSYSTEM/*/etc/profile.d/init.sh
done
