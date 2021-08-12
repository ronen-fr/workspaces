#!/usr/bin/python3

from bs4 import BeautifulSoup
import re
import requests
import argparse
import subprocess
import sys
import os
import pathlib
from subprocess import Popen

pulp_base='https://pulpito.ceph.com'
node_base='.front.sepia.ceph.com'

# create a dictionary of run times
def find_times(soup, is_v):
    all_times={}
    running_jobs = soup.find_all(attrs={ 'class'  :re.compile(".*job_running.*")})
    for jb in running_jobs:
        #print (jb)
        #jbid = re.search('[0-9]+', jb.find(attrs={'data-title':'Job ID'}).text)[0]
        jbid = jb.find(attrs={'data-title':'Job ID'}).text.strip()        
        trun = jb.find(attrs={'data-title':'Runtime'}).text.strip()
        if is_v:
            print(f"     {jbid}  == {trun}")
        all_times[jbid] = trun
    return all_times
    

#counting the number of files in a remote node directory
def remote_crash_files_count(node_ad, pth):
    remote_cmd = f'sudo ls {pth}'
    #print (remote_cmd)
    core1 = subprocess.Popen(["echo", "ssh", "-q", node_ad, remote_cmd],  stdout=subprocess.PIPE)
    core1_st =  subprocess.Popen([ 'wc', '-l' ], stdin=core1.stdout, stdout=subprocess.PIPE)
    ot, er = core1_st.communicate()
    return int(ot)
    
def remote_crash_files_Ccount(node_ad, pth):
    remote_cmd = f'sudo ls {pth}'
    #print (remote_cmd)
    core1 = subprocess.Popen(["echo", "ssh", "-q", node_ad, remote_cmd],  stdout=subprocess.PIPE)
    core1_st =  subprocess.Popen([ 'wc', '-c' ], stdin=core1.stdout, stdout=subprocess.PIPE)
    ot, er = core1_st.communicate()
    return int(ot)

def look_for_core(node_name, is_v):
    node_ad = f"{node_name}{node_base}"
    kgn = subprocess.Popen(["ssh-keygen", "-q", "-R", node_ad], stderr=subprocess.DEVNULL, stdout=subprocess.PIPE)
    kgn_out, kgn_er = kgn.communicate()

    crash_dir_nf =  remote_crash_files_count(node_ad, '/var/lib/ceph/crash')
    postd_dir_nf =  remote_crash_files_count(node_ad, '/var/lib/ceph/crash/posted')
    ubunt_dir_nf =  remote_crash_files_Ccount(node_ad, '/home/ubuntu/cephtest/archive/coredump')
    #print (ubunt_dir_nf)
    
    if is_v:
        print (f'     -{node_name}-- files in crash:{crash_dir_nf}, crash/posted:{postd_dir_nf}')
        #ubu_ls = subprocess.Popen(["ssh", "-q", node_ad, "sudo ls /home/ubuntu/cephtest"],  stdout=subprocess.PIPE)
        #otu, eru = ubu_ls.communicate()
        #print (f"    - ubuntu: {otu}")

    if (crash_dir_nf > 1):
        crs_nf = subprocess.Popen(["ssh", "-q", node_ad, "sudo ls /var/lib/ceph/crash"],  stdout=subprocess.PIPE)
        ot, er = crs_nf.communicate()
        print (f"   $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ \n{ot}")

    if (crash_dir_nf > 1):
        pst_nf = subprocess.Popen(["ssh", "-q", node_ad, "sudo ls /var/lib/ceph/crash/posted"],  stdout=subprocess.PIPE)
        ot2, er = pst_nf.communicate()
        print (f"   $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ \n{ot2}")

    if (ubunt_dir_nf > 1):
        ubu_ls = subprocess.Popen(["ssh", "-q", node_ad, "sudo ls /home/ubuntu/cephtest/archive/coredump"],  stdout=subprocess.PIPE)
        ot3, er = ubu_ls.communicate()
        print (f"   $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ \n{ot3}")
  

def jobs_category(cat_name, cat, is_v, times, is_times):
    for jb in cat:
        jbid_tree = jb.find(attrs={'data-title':'ID:'})
        jbid = jbid_tree.a.next_sibling.next_sibling.text
        jbst = jb.find(attrs={'data-title':'Status:'}).a.string
        if is_v or True:
            if is_times:
                print (f"  ({cat_name}) {jbid} -> {jbst} {times[jbid]}")
            else:
                print (f"  ({cat_name}) {jbid} -> {jbst}")

        nds = jb.find(attrs={'data-title':'Targets:'}).find_all('a')
        for nd in nds:
            #print ('   -   ', nd.text)
            look_for_core(nd.text, args.verbose)
        

parser =  argparse.ArgumentParser(description='the nodes of running jobs')
parser.add_argument('-v', '--verbose', action='store_true')
parser.add_argument('-d', '--deads', action='store_true', help='visit dead jobs')
parser.add_argument('-t', '--times', action='store_true', help='fetch run-time data')
parser.add_argument('run_name', help='rfriedma/...')
args = parser.parse_args()

#r=requests.get("https://pulpito.ceph.com/khiremat-2021-08-05_17:51:48-fs:workload-wip-khiremat-test-kernel-exclude-failures-distro-basic-smithi/detail")
run_full_path = f"{pulp_base}/{args.run_name}/detail"
print (run_full_path)
r = requests.get(run_full_path)
s = BeautifulSoup(r.text,"html.parser")

if args.times:
    # fetch run time for 'running' jobs
    short_path = f"{pulp_base}/{args.run_name}"
    r_short = requests.get(short_path)
    s_short = BeautifulSoup(r_short.text,"html.parser")
    allt = find_times(s_short, args.verbose)
else:
    allt = {}
    
running_jobs = s.find_all('div', attrs={ 'class'  :re.compile(".*job_running.*")})
jobs_category('running', running_jobs,  args.verbose, allt, args.times)

if args.deads:
    dead_jobs = s.find_all('div', attrs={ 'class'  :re.compile(".*dead.*")})
    jobs_category('dead', dead_jobs,  args.verbose, allt, False)


    
