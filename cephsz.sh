#!/bin/bash

# collect all relevant directories. Currently - by hand

uptodate="xxxxxxx"
fetch_origin=true
fetch_upstream=true

function clear_dirname()
{
    echo $1 | sed 's=/home/rfriedma/=-- -- =' | sed 's=src/= =' | sed 's=/ceph= -- -- -- =' |  awk -e '{printf "%s",substr($0,1,18);}'
}

function short_st()
{
    cst=`git status -uno --ignore-submodules=all`
    echo $cst | grep -q 'up to date' && uptodate="up-to-date"
    echo $cst | grep -q 'behind'     && uptodate="behind    "
    echo $cst | grep -q 'detached'   && uptodate="detached  "
    echo $cst | grep -q 'diverged'   && uptodate="diverged  "
}

function refs_diff()
{
    if git ls-remote  --get-url origin | grep -q ronen && git ls-remote  --get-url upstream | grep -q ceph; then
	if $fetch_upstream; then
	    git fetch upstream master > /dev/null 2>&1
	fi
	df_m_om=`git rev-list --count master..origin/master | sed 's/ //'`
	#df_om_m=`git rev-list --count origin/master..master | sed 's/ //'`
	#df_um_om=`git rev-list --count upstream/master..origin/master | sed 's/ //'`
	df_om_um=`git rev-list --count origin/master..upstream/master`
	echo -n "[./o: $df_m_om o-ms/u-ms:$df_om_um]               " | awk -e '{printf "%s",substr($0,1,26);}'
    else
	echo -n "{{xx-rt-xx}}                     " | awk -e '{printf "%s",substr($0,1,26);}'
    fi
}

function modified_files()
{
    if git ls-remote  --get-url origin | grep -q ronen ; then
	n_modified=`git status  --ignore-submodules --porcelain | grep -e '^ [MDR]' | wc -l`
	n_added=`git status  --ignore-submodules --porcelain | grep -e '^ A' | wc -l`
	echo -n "<M:$n_modified - A:$n_added>   " | awk -e '{printf "%s",substr($0,1,16);}'
    else
	echo -n "<.....>                     " | awk -e '{printf "%s",substr($0,1,16);}'
    fi
}

function old_branches()
{
     git log --date=relative --pretty=oneline -g | awk -f <(cat - <<'EOD'

BEGIN { br_count = 0; }
/moving from/ {
	#print $0
	br=$8
	if (seen[$8]) {
		next;
	}
	seen[$8] = $NF
	if (br_count>4) {
		exit 0;
	}
	br_count=br_count+1
	
	date_from = substr($0,match($0,"{.*}"),RLENGTH);
	printf "-\t%8.8s %-15.15s %s\n",substr($1,1,8),date_from,$8;
}

EOD
)
}


function oneceph()
{
    d=$1
    echo
    #echo '---------------------'
    #echo $d
    #echo
    cd $d

    if $fetch_origin; then
        git fetch  > /dev/null 2>&1
    fi

    #git --no-pager log -1 --format="%h %s"
    comt=`git --no-pager log -1 --format="%h %s"`
    branch=`git rev-parse --abbrev-ref HEAD`
    dirt="$(clear_dirname $d)"

    short_st
    
    echo "$dirt -- -- $uptodate --  $branch      $(refs_diff)"
    echo "	$comt  $(modified_files)"

    # make sure we have a "normal" origin/upstream setting
    git ls-remote  --get-url origin | grep -q ronen || echo "  ******* irregular origin ***********"
    
    
    if [ -e build ]; then
	ls -ld build | awk  '{ printf "\n\t%s-%s %s  %s",$7,$6,$8,$9; }'
        if [ -e build/build.ninja ]; then
	    ls -ld build/build.ninja | awk '{ print "  Ninja: " $7 "-" $6 " " $8 " " $9 }'
        fi
    fi
    echo

    #git log --date=relative --pretty=oneline -g | grep 'moving from' | cut -n -b1-8,46- | cut -d\   -f1,2,3,7 | grep -v master | sed -e 's/^/    /;4q'
    old_branches
}

ac="$HOME/tmp/rf_sc/ceph "
ac1=" fx7 scr6 scr5 master cln_may fix_4 s2 scrub1 "
for u in $ac1; do
    ac="$ac $HOME/src/$u/ceph"
done

[ $# -gt 0 ] && fetch_upstream=false
[ $# -gt 1 ] && fetch_origin=false

for d in $ac; do
    oneceph $d
done
    
