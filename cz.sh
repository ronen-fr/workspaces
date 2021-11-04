#!/bin/bash

# collect all relevant directories. Currently - by hand

uptodate="xxxxxxx"
fetch_origin=true
fetch_upstream=true

function clear_dirname()
{
  if [ $(hostname) == "rflap" ]; then
    echo $1 | sed 's=/home/rfriedma/=-- -- =' | sed 's=src/= =' | sed 's=/ceph= -- -- -- =' |  awk -e '{printf "%s",substr($0,1,18);}'
  else
    echo $1 | sed 's=/home/ronen-fr/=-- -- =' | sed 's=src/= =' | sed 's=/ceph= -- -- -- =' |  awk -e '{printf "%s",substr($0,1,18);}'
  fi
}

function short_st()
{
    cst=`git status -uno --ignore-submodules=all`
    echo $cst | grep -q 'up to date' && uptodate="up-to-date"
    echo $cst | grep -q 'ahead'      && uptodate="ahead     "
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
	echo -n "{{xx-rt-xx}}                     " | awk -e '{printf "%s",substr($0,1,30);}'
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
/moving from master/ {next;}
/moving from/ {
	#print $0
	br=$8
	if (seen[$8]) {
		next;
	}
	seen[$8] = $NF
	if (br_count>6) {
		exit 0;
	}
	br_count=br_count+1
	
	date_from = substr($0,match($0,"{.*}"),RLENGTH);
	printf "-\t%8.8s %-15.15s %s\n",substr($1,1,8),date_from,$8;
}

EOD
)
}

function build_dir_info()
{
  if [ -e build ]; then
    ls -ld build | awk  '{ printf "\n\t%s-%s %s  %s",$7,$6,$8,$9; }'
    if [ -e build/compile_commands.json ]; then
      # clang / gcc ?  crimson?
      comp="G++"
      grep -i -q clang build/compile_commands.json && comp="Clang"
      crimson="Classic"
      grep -i -q SEASTAR build/compile_commands.json && crimson="Crimson"
      echo -e -n " $comp  $crimson  \t"
    else
      echo -n " [[no script]] "
    fi
    if [ -e build/build.ninja ]; then
      ls -ld build/build.ninja | awk '{ print " { Ninja: " $7 "-" $6 " " $8 " " $9 " }" }'
    else
      echo
    fi
  else
    echo -e "\n\t-- no build"
  fi
}

function oneceph()
{
    d=$1
    echo
    #echo '---------------------'
    #echo $fetch_origin
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
    
    build_dir_info
    #if [ -e build ]; then
    #	ls -ld build | awk  '{ printf "\n\t%s-%s %s  %s",$7,$6,$8,$9; }'
    #    if [ -e build/build.ninja ]; then
    #	    ls -ld build/build.ninja | awk '{ print "  Ninja: " $7 "-" $6 " " $8 " " $9 }'
    #    fi
    #fi
    echo

    #git log --date=relative --pretty=oneline -g | grep 'moving from' | cut -n -b1-8,46- | cut -d\   -f1,2,3,7 | grep -v master | sed -e 's/^/    /;4q'
    old_branches
}

if [ $(hostname) == "rflap" ]; then
  ac1="fx7 master rf_sc fix_4 cln_may scrub0 scrub1 s2 scr5 scr6"
  for u in $ac1; do
    ac="$ac $HOME/src/$u/ceph"
  done
else
  ac="/home/ronen-fr/tmp2/rt1/ceph /home/ronen-fr/tmp2/rt2/ceph /home/ronen-fr/tmp2/rt3/ceph /home/ronen-fr/tmp2/rt4/ceph /home/ronen-fr/tmp2/bg5/ceph /home/ronen-fr/tmp2/pa1/ceph"
  ac1=" br1 br2_crimson br3_classic br5_classic crimson_321 lto map markhpc "
  for u in $ac1; do
    ac="$ac $HOME/src/$u/ceph"
  done
fi

[ $# -gt 0 ] && fetch_upstream=false
[ $# -gt 1 ] && fetch_origin=false

for d in $ac; do

    oneceph $d

done
    
