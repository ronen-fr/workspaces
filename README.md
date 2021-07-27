# workspaces
scripts for managing workspaces
===============================

cephsz.sh
---------
The fullest query of the local repositories.
Sample output:

```
-- -- tmp/rf_sc -- -- -- xxxxxxx --  wip-ronenf-double-jeopardy      <M:6-A:0>  [0-0 us:0-0]               
	861f80ea8ff osd/scrub: remove reliance of Scrubber objects' logging on the PG

	25-Jul 14:34  build  Ninja: 24-Jul 17:34 build/build.ninja

-	861f80ea {29 hours ago}  wip-ronenf-scrub-prefix
-	861f80ea {29 hours ago}  wip-ronenf-double-jeopardy
-	fa8f0756 {2 days ago}    master
-	91afa17c {2 days ago}    wip-ronenf-scrub-sched
-	5841b061 {3 weeks ago}   wip-ronenf-list-object

-- --  fx7 -- -- - -- -- up-to-date --  wip-ronenf-scrub-sch-bug2      <M:4-A:0>  [230-0 us:230-0]              
	5e913149880 fixing rescheduling at end of scrub

	23-Jul 16:30  build  Ninja: 23-Jul 15:09 build/build.ninja

-	87a3f13d {4 days ago}    wip-ronenf-scrub-sch-bug1
-	e2489d75 {8 days ago}    wip-ronenf-scrub-sched
-	ee125f24 {9 days ago}    master
-	da5d094f {4 weeks ago}   wip-ronenf-pac-50346
...
```

![Alt text](aux/cephsz-annotated-1.jpg?raw=true "V0.1")


