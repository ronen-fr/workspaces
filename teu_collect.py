#!/usr/bin/python3

import sys
import argparse
import datetime
import subprocess
import tempfile
import os
import pathlib
import re
import fnmatch
import threading
from subprocess import Popen

homedir = pathlib.Path.cwd()
log_exist=False

# file patterns:
pat_osd_num=re.compile(r'(ceph-)*osd.(?P<osdn>[0-9]+).log(.gz)*')
#pat_osd_num=re.compile(r'(?:(ceph-)*)osd.(?P<osdn>[0-9]+).log(.gz)*')
#pat_osd_num=re.compile(r'osd.(?P<osdn>[0-9]+).log')
core_path_parts=re.compile(r'.*/(?P<rmt>[^/]+)/coredump/(?P<unzped_name>.*core)(.gz)*')
#crash_path_parts=re.compile(r'.*/(?P<rmt>((trial)|(smithi))[0-9]+)/crash/(?P<instance>.*)')
crash_path_parts=re.compile(r'.*/(?P<rmt>[^/]+)/crash/(posted/)*(?P<instance>.*)')

#clogs_path_parts=re.compile(r'.*/(?P<rmt>((trial)|(smithi))[0-9]+)/log/(?P<unzped_name>ceph.log).gz')
clogs_path_parts=re.compile(r'.*/[^/]*?(?P<rmt>\d+)/log/(?P<unzped_name>ceph.log).gz')

logs={}
num_osd_lines = 800000

def locate_logs(p, n):
    global log_exist
    #al=list(p.glob('remote/*/log/ceph-osd.*.log.gz')) + list(p.glob('remote/*/log/osd.*.log')) + list(p.glob('remote/ubu*/log/*/ceph-osd.*.log.gz'))
    al=list(p.rglob(r'*osd.[0-9]*.log*'))
    
    if (len(al) > 0):
        log_exist=True
        return [ True, al ]

    else :
        print ('No logs!!!')
        log_exist=False
        return [ False, al ]

def cp_cluster_logs(p, n):
   clogs=list(p.glob('remote/*/log/ceph.log.gz'))
   for cfn in clogs:
      print('cluster log: ', cfn)
      clog_parts = clogs_path_parts.search(str(cfn))
      if clog_parts is None:
          print(f'The cluster log path ({cfn}) does not correspond to the expected pattern')
          continue

      print('rmt: ', clog_parts.group('rmt'), clog_parts.group('unzped_name'))

      target_wo = homedir / n / ( 'c' + clog_parts.group('rmt') + '_ceph.log'  )
      print('target: ', target_wo)

      target_fd = open(target_wo, 'w')
      zct = subprocess.Popen([ 'zcat', cfn ], stdout=subprocess.PIPE)
      # required if the date in the cluster log is not formatted:
      #zct = subprocess.Popen([ 'zcat', cfn ], stdout=subprocess.PIPE)
      #tstamp= subprocess.Popen(["gawk -e ' { all=$_; x=\"@\"$1; cmd=\"\'\" date --rfc-3339=ns -d \"\'\"x\"\'\" \"\'\"; cmd | getline z; close(cmd); z1=substr(z,0,length(z)-12); sub(\".*\",z1,$1); print $_  } ' " ], shell=True, stdin=zct.stdout, stdout=target_fd)
      tstamp= subprocess.Popen(["cat" ], shell=True, stdin=zct.stdout, stdout=target_fd)
      zct.stdout.close()
      tstamp.communicate()


def help_cpcmd():
    print('scp ~/src/teu_collect rfriedma@teuthology.front.sepia.ceph.com:/home/rfriedma/teu_collect')
    print('ssh rfriedma@teuthology.front.sepia.ceph.com chmod +x /home/rfriedma/teu_collect')


def list_main(is_verbose, p, n):
    # do we have logs at all (for most 'dead' jobs - we won't have)
    [gotlogs, lgs] = locate_logs(p, n)
    if is_verbose:
        print(gotlogs)
        print(lgs)

    # list the OSDs
    #subprocess.run(["find", "remote", "-iname", "ceph-osd.log.gz", "-ls"], check=False)
    # search for core files
    print('cores:')
    subprocess.run(["find", p/"remote", "-iname", "core.*", "-ls"], check=False)
    return lgs


def cp_logs(p, n, lgs, must_not_bg, do_backtraces=True):
    global pat_osd_num
    print('cp_logs')
    print(lgs)

    for lpath in lgs:
        osdnum = pat_osd_num.search(lpath.name).group('osdn')
        #logs[osdnum.group('osdn')] = lpath
        logs[osdnum] = lpath
        target = homedir / n / osdnum
        print(lpath.name, ' -> ' , osdnum, '\t -> ', target)

        target_fd = open(target, 'w')

        if (fnmatch.fnmatch(lpath, '*.gz')):
            zct = subprocess.Popen([ 'zcat', lpath ], stdout=subprocess.PIPE)
        else:
            zct = subprocess.Popen([  'cat', lpath ], stdout=subprocess.PIPE)
        grp1= subprocess.Popen([ 'grep', '-a', '-n', '-v', 'bluefs' ], stdin=zct.stdout, stdout=subprocess.PIPE)
        grp2= subprocess.Popen([ 'grep', '-a', '-v',  'bluest' ], stdin=grp1.stdout, stdout=subprocess.PIPE)
        tl1= subprocess.Popen([ 'tail', str(-num_osd_lines) ], stdin=grp2.stdout, stdout=subprocess.PIPE)
        fld= subprocess.Popen([ 'fold', '-s', '-w', '500' ], stdin=tl1.stdout, stdout=target_fd)
        zct.stdout.close()
        if must_not_bg:
            fld.communicate()

    if do_backtraces:
        bt_threads = []
        for osdnum, lpath in logs.items():
            t = threading.Thread(target=extract_backtraces,
                                 args=(lpath, osdnum, homedir / n))
            t.start()
            bt_threads.append(t)
        for t in bt_threads:
            t.join()

    return logs
    # zcat logf | grep -v bluestore | grep -v bluefs | tail -f 300000 | fold -s -w500 > ~/tn/n


def extract_backtraces(lpath, osdnum, target_dir):
    if fnmatch.fnmatch(lpath, '*.gz'):
        cat_cmd = ['zcat', str(lpath)]
    else:
        cat_cmd = ['cat', str(lpath)]

    # single pass: track the last-seen timestamp, record Backtrace occurrences
    pat_timestamp = re.compile(r'(\d{4}-\d{2}-\d{2}[T_ ]\d{2}:\d{2}:\d{2}[.,]\d+)')
    cat_proc = subprocess.Popen(cat_cmd, stdout=subprocess.PIPE)
    backtrace_hits = []
    last_timestamp = 'unknown'
    for lineno, raw_line in enumerate(cat_proc.stdout, 1):
        line = raw_line.decode('utf-8', errors='replace')
        ts_match = pat_timestamp.search(line)
        if ts_match:
            last_timestamp = ts_match.group(1).replace(' ', '_').replace(',', '.')
        if 'Backtrace' in line:
            backtrace_hits.append((lineno, last_timestamp))
    cat_proc.wait()

    if not backtrace_hits:
        return

    for lineno, timestamp in backtrace_hits:

        start = max(1, lineno - 2000)
        end = lineno + 2000

        outname = f'{osdnum}_{timestamp}_{lineno}'
        outpath = target_dir / outname
        print(f'Backtrace: osd.{osdnum} line {lineno} -> {outpath}')

        cat_proc2 = subprocess.Popen(cat_cmd, stdout=subprocess.PIPE)
        with open(outpath, 'w') as outfd:
            sed_proc = subprocess.Popen(['sed', '-n', f'{start},{end}p'],
                                        stdin=cat_proc2.stdout, stdout=outfd)
            cat_proc2.stdout.close()
            sed_proc.communicate()


def cp_cores(is_verbose, p, n) :
    print('copying possible core files')
    al=list(p.glob('remote/*/coredump/*.*.core.gz')) + list(p.glob('remote/*/coredump/*.*.core'))
    if (len(al) > 0):
        print('found cores')
        target = homedir / n
        for cfn in al:
            core_parts = core_path_parts.search(str(cfn))
            if core_parts is None:
                print(f'The core path ({cfn}) does not correspond to the expected pattern')
                return
            if is_verbose:
                print('cfn: ', cfn)
                print('core_parts: ', core_parts.group(0))
                #print('unzp: ', core_parts.group('unzped_name'))
            target_wo = target / ( core_parts.group('rmt') + '__' + core_parts.group('unzped_name')  )
            print(f'Core file {cfn} -> {target_wo}\n')
            target_fd = open(target_wo, 'x')
            if (fnmatch.fnmatch(cfn, '*.gz')):
                zct = subprocess.run([ 'zcat', cfn ], stdout=target_fd)
            else:
                zct = subprocess.run([  'cat', cfn ], stdout=target_fd)
            target_fd.close()

            #subprocess.run(['cp', '-f', cfn, target_wgz], check=False)
            #subprocess.run(['gunzip', target_wgz], check=False)
            subprocess.run(['file', target_wo], check=False)

def cp_crashes(p,n) :
    print('copying possible crash')
    target = homedir / n
    al=list(p.glob('remote/*/crash'))
    if (len(al) > 0):
        for cfn in al:
            if os.path.exists(cfn / 'posted'):
                cfn = cfn / 'posted'
            with os.scandir(cfn) as it:
                for insta in it:
                    if not insta.name.startswith('.'):
                        print('Crash insta: ', insta.name)

                        subprocess.run(['mkdir', target/insta.name])
                        subprocess.run(['cp ' + str(cfn) + '/' + insta.name + '/log ' + str(target/insta.name)], shell=True, check=False)
                        subprocess.run(['cp ' + str(cfn) + '/' + insta.name + '/meta ' + str(target/insta.name)], shell=True, check=False)

def parse_log(d, n, oslog) :
    print ('parsing ', oslog, ' into /tmp/T_*, /tmp/Q_*, *_scr')
    subprocess.run(['grep -a -n signal ' + str(oslog) + ' > /tmp/Q_' + str(n)], shell=True)
    subprocess.run([r"grep -E -a -- 'scrubber|sched-queue|sched_scrub' " + str(oslog) + ' > ' + str(oslog) + '_scr' ], shell=True)
    subprocess.run(['tail -40 ' + str(oslog) + ' > /tmp/T_' + str(n)], shell=True)


def parse_logs(p, n) :
    target = homedir / n 
    nlist=list(range(0,10))
    for osn in nlist:
        if os.path.isfile(target / str(osn)) :
            parse_log(target,osn,  target / str(osn))


def extra_symlinks(p, n) :
    target = homedir / n / '_'
    if target.is_symlink() or target.exists() :
        os.unlink(target)
    print (f'symlinking from {p} to {target}')
    os.symlink(p, target)



parser = argparse.ArgumentParser(description='collect cores and logs')
parser.add_argument('-v', '--verbose', action='store_true')
parser.add_argument('--parse', action='store_true', help='extract info from the osd logs')
parser.add_argument('--logs', action='store_true', help='unzip log tails')
parser.add_argument('--no-cores', action='store_true')
parser.add_argument('--no-backtrace', action='store_true', help='skip extracting Backtrace surroundings from OSD logs')
parser.add_argument('-f', '--force', action='store_true', help='OK to use existing target dir')
parser.add_argument('-s', '--symlink', action='store_true', help='create symlinks to some conf files')
parser.add_argument('path', nargs='?', default=None, help='/a/... (optional; if omitted, searches /a/*/tnum)')
parser.add_argument('tnum', help='test number')

args = parser.parse_args()

if args.path:
    fpath = pathlib.Path('/a') / args.path / args.tnum
else:
    import glob
    matches = glob.glob(f'/a/*/{args.tnum}')
    if len(matches) == 0:
        print(f'No test directory found matching /a/*/{args.tnum}')
        sys.exit(1)
    if len(matches) > 1:
        print(f'Multiple matches found for /a/*/{args.tnum}:')
        for m in matches:
            print(f'  {m}')
        sys.exit(1)
    fpath = pathlib.Path(matches[0])
print('fpath: ', fpath)

if args.verbose:
    print('Path: ', args.path)
    print('#: ', args.tnum)
    help_cpcmd()
    print('\n-----------------------------\n\n')

target_dir = homedir / args.tnum
if target_dir.exists() :
    print('Target dir ', target_dir, 'already_exists!!!!!!!!')
    if args.logs and not args.force :
        sys.exit(1)
else :
    os.mkdir(target_dir)

all_logs = list_main(args.verbose, fpath, args.tnum)

subprocess.run(['cp', fpath/'teuthology.log', target_dir], check=False)
subprocess.run(['cat -n ' + str(fpath/'teuthology.log') + ' | tail -500000 |fold -s -w 500 > ' + str(target_dir / 'teu')], shell=True, check=False)

if not args.no_cores :
    cp_crashes(fpath, args.tnum)

if not args.no_cores :
    cp_cores(args.verbose, fpath, args.tnum)

if log_exist and args.logs :
    # collecting the logs can be background-run - but only if
    # not parsing them afterwards
    cp_logs(fpath, args.tnum, all_logs, args.parse, not args.no_backtrace)

if args.parse or args.logs :
    parse_logs(fpath, args.tnum)

cp_cluster_logs(fpath, args.tnum)
    
# if args.symlink :
extra_symlinks(fpath, args.tnum)

sys.exit(0)

