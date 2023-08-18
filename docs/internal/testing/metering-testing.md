# Metering System Testing

## Test 1: 08-17-23, 18:00-23:00 UTC
Ran tests for 5 hours, with
* 1 cpu.small deployment running for entire testing duration
* 1 cpu.medium deployment scheduled to run for 5 minutes, randomly each hour
* 10 0.2 GB files, uploaded for entire testing duration
* 10 0.2 GB files, uploaded randomly for 30 minutes out of each hour

* Expected:
    * 300 minutes of cpu.small usage
    * 29 minutes of cpu.medium usage (including cold start time)
    * 3 GB/HR used on average
* Actual:
    * 302 minutes of cpu.small usage 
        * 2 minutes of usage reported during 23:00-23:10
        * Pod termination was likely slightly delayed (on exit, testing client sends delete requests sychronously).
    * 28 minutes of cpu.medium usage 
        * within acceptable range of error
    * 2.99 GB/HR used on average 

* Notes: 
    * `EFSDescribeFileSystem` doesn't report the most up-to-date data: there seems to be an approximate ~30 minute delay. (I.E immediately after uploading 2 GB to the PV, `mothership volumes list` will still report no data until around 30 minutes later). For example, metering reports no storage used for first 30 minutes after upload at `18:00`, and also reported 2 GB/Hr of storage used from `23:00-23:59`, even though all files were removed at `23:00`. This can be seen in the fine grain data below.

Detailed data below:

### Compute Data
```
select sum(usage) from compute_hourly where workspace_id='andimetering' and end_time>='2023-08-17 19:00:00+00' and end_time<='2023-08-18 00:00:00+00' and shape='cpu.small'
metering-> ;
 sum
-----
 302
(1 row)

select query_end, minutes from compute_fine_grain where namespace='ws-andimetering' and query_end>'2023-08-17 18:00:00+00' and query_end<='2023-08-18 00:00:00+00' and shape='cpu.small';
       query_end        | minutes
------------------------+---------
 2023-08-17 18:10:00+00 |      10
 2023-08-17 18:20:00+00 |      10
 2023-08-17 18:30:00+00 |      10
 2023-08-17 18:40:00+00 |      10
 2023-08-17 18:50:00+00 |      10
 2023-08-17 19:00:00+00 |      10
 2023-08-17 19:10:00+00 |      10
 2023-08-17 19:20:00+00 |      10
 2023-08-17 19:30:00+00 |      10
 2023-08-17 19:40:00+00 |      10
 2023-08-17 19:50:00+00 |      10
 2023-08-17 20:00:00+00 |      10
 2023-08-17 20:10:00+00 |      10
 2023-08-17 20:20:00+00 |      10
 2023-08-17 20:30:00+00 |      10
 2023-08-17 20:40:00+00 |      10
 2023-08-17 20:50:00+00 |      10
 2023-08-17 21:00:00+00 |      10
 2023-08-17 21:10:00+00 |      10
 2023-08-17 21:20:00+00 |      10
 2023-08-17 21:30:00+00 |      10
 2023-08-17 21:40:00+00 |      10
 2023-08-17 21:50:00+00 |      10
 2023-08-17 22:00:00+00 |      10
 2023-08-17 22:10:00+00 |      10
 2023-08-17 22:20:00+00 |      10
 2023-08-17 22:30:00+00 |      10
 2023-08-17 22:40:00+00 |      10
 2023-08-17 22:50:00+00 |      10
 2023-08-17 23:00:00+00 |      10
 2023-08-17 23:10:00+00 |       2
(31 rows)

select sum(usage) from compute_hourly where workspace_id='andimetering' and end_time>='2023-08-17 19:00:00+00' and end_time<='2023-08-18 00:00:00+00' and shape='cpu.medium'
;
 sum
-----
  28
(1 row)

select query_end, minutes from compute_fine_grain where namespace='ws-andimetering' and query_end>='2023-08-17 18:00:00+00' and query_end<='2023-08-18 00:00:00+00' and shape='cpu.medium';
       query_end        | minutes
------------------------+---------
 2023-08-17 18:40:00+00 |       4
 2023-08-17 18:50:00+00 |       4
 2023-08-17 19:50:00+00 |       6
 2023-08-17 21:20:00+00 |       8
 2023-08-17 23:00:00+00 |       6
(5 rows)

```

### Storage Data
```
select avg(size_bytes) from storage_hourly where workspace_id='andimetering' and end_time>='2023-08-17 19:00:00+00' and end_time<'2023-08-18 00:00:00+00';
         avg
---------------------
 2993429913.60000000
(1 row)


select time, size_bytes from storage_fine_grain where workspace='andimetering' and time>='2023-08-17 19:00:00+00' and time<='2023-08-18 00:00:00+00';

          time          | size_bytes
------------------------+------------
 2023-08-17 18:10:00+00 |      12288
 2023-08-17 18:20:00+00 |      12288
 2023-08-17 18:30:00+00 |      12288
 2023-08-17 18:40:00+00 | 1600057344
 2023-08-17 18:50:00+00 | 3200102400
 2023-08-17 19:00:00+00 | 3200102400
 2023-08-17 19:10:00+00 | 3200102400
 2023-08-17 19:20:00+00 | 3200102400
 2023-08-17 19:30:00+00 | 2800091136
 2023-08-17 19:40:00+00 | 2800091136
 2023-08-17 19:50:00+00 | 3600113664
 2023-08-17 20:00:00+00 | 3600113664
 2023-08-17 20:10:00+00 | 3600113664
 2023-08-17 20:20:00+00 | 3600113664
 2023-08-17 20:30:00+00 | 3600113664
 2023-08-17 20:40:00+00 | 2000068608
 2023-08-17 20:50:00+00 | 2000068608
 2023-08-17 21:00:00+00 | 3600113664
 2023-08-17 21:10:00+00 | 3600113664
 2023-08-17 21:20:00+00 | 3600113664
 2023-08-17 21:30:00+00 | 3600113664
 2023-08-17 21:40:00+00 | 3000096768
 2023-08-17 21:50:00+00 | 3000096768
 2023-08-17 22:00:00+00 | 4000124928
 2023-08-17 22:10:00+00 | 4000124928
 2023-08-17 22:20:00+00 | 4000124928
 2023-08-17 22:30:00+00 | 4000124928
 2023-08-17 22:40:00+00 | 3400108032
 2023-08-17 22:50:00+00 | 4000124928
 2023-08-17 23:00:00+00 | 4000124928
 2023-08-17 23:10:00+00 | 4000124928
 2023-08-17 23:20:00+00 | 4000124928
 2023-08-17 23:30:00+00 | 4000124928
 2023-08-17 23:40:00+00 |      12288
 2023-08-17 23:50:00+00 |      12288
 2023-08-18 00:00:00+00 |      12288
(36 rows)
```
