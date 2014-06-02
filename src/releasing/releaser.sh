#!/bin/bash

REPOS="aii CAF CCM cdp-listend configuration-modules-core configuration-modules-grid LC ncm-cdispd ncm-ncd ncm-query ncm-lib-blockdevices"
RELEASE=""
BUILD=""

RELEASE_ROOT=$(dirname $(readlink -f "$0"))

function echo_warning {
  echo -e "\033[1;33mWARNING\033[0m  $1"
}

function echo_error {
  echo -e "\033[1;31mERROR\033[0m  $1"
}

function echo_success {
  echo -e "\033[1;32mSUCCESS\033[0m  $1"
}

function echo_info {
  echo -e "\033[1;34mINFO\033[0m  $1"
}

if [[ -n $1 ]]; then
    RELEASE=$1
else
    echo_error "Release version not provided"
    echo "    Based on the date, you should probably be working on $(date +%y.%m)"
    echo
    echo "USAGE: releaser.sh RELEASE_NUMBER [RELEASE_CANDIDATE]"
    exit 3
fi

if [[ -n $2 ]]; then
    BUILD=$2
else
    echo_warning "You are running a final release, please ensure you have built at least one release candidate before proceeding!"
fi

VERSION="$RELEASE"
if [[ -n $BUILD ]]; then
    VERSION="$RELEASE-rc$BUILD"
fi

details=""

if gpg-agent; then
    if gpg --yes --sign $0; then
        echo -n "Preparing repositories for release... "
        cd $RELEASE_ROOT
        for r in $REPOS; do
            if [[ ! -d $r ]]; then
                git clone -q git@github.com:quattor/$r.git
            fi
            cd $r
            git branch -r | grep $RELEASE > /dev/null && git checkout -q quattor-$RELEASE || git checkout -q master
            details="$details\n$r\t$(git branch | grep '^*')"
            cd ..
        done
        echo "Done."
        echo
        echo -e $details | column -t
        echo
        echo "We will build $VERSION from the branches shown above, continue with release? yes/NO"
        echo -n "> "
        read prompt
        if [[ $prompt == "yes" ]]; then
            for r in $REPOS; do
                echo_info "---------------- Releasing $r ----------------"
                cd $r
                mvn -q -DautoVersionSubmodules=true -Dgpg.useagent=true -Darguments=-Dgpg.useagent=true -B -DreleaseVersion=$VERSION clean release:prepare release:perform
                if [[ $? -gt 0 ]]; then
                    echo_error "RELEASE FAILURE"
                    exit 1
                fi
                cd ..
                echo
            done

            echo_success "---------------- Releases complete, building yum repositories ----------------"

            cd $RELEASE_ROOT
            mkdir -p target/

            echo_info "Collecting RPMs"
            mkdir -p target/$VERSION
            find src/ -type f -name \*.rpm | grep /target/checkout/ | xargs -I @ cp @ target/$VERSION/

            cd target/

            echo_info "Signing RPMs"
            rpm --resign $VERSION/*.rpm

            echo_info "Creating repository"
            createrepo $VERSION/

            echo_info "Signing repository"
            gpg --detach-sign --armor $VERSION/repodata/repomd.xml

            echo_info "Creating repository tarball"
            tar -cjf quattor-$VERSION.tar.bz2 $VERSION/
            echo_info "Repository tarball built: target/quattor-$VERSION.tar.bz2"

            echo_success "RELEASE COMPLETED"
        else
            echo_error "RELEASE ABORTED"
            exit 2
        fi
    fi
fi
