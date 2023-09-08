# Usage Metering

## General
`go-pkg/metering` contains all type definitions and SQL related code.

Importantly, table names are defined in `go-pkg/metering/util.go`.

## Compute Resource Usage Information
Raw usage information is gathered matching the following schema:
```
    query_id uuid not null
    namespace text NOT NULL,
    deployment_name text,
    pod_name text NOT NULL,
    shape text,
    query_start TIMESTAMPTZ NOT NULL,
    query_end TIMESTAMPTZ NOT NULL,
    query_window INTERVAL NOT NULL,
    minutes REAL
    PRIMARY KEY (namespace, deployment_name, pod_name)
```
We don't store cluster information as namespaces must be unique, accross all clusters.

This data is stored in `MeteringTableComputeFineGrain` defined in the `go-pkg/metering` package.

Assuming consistent query intervals of 10 minutes, A single pod requires ~36 kB of storage, per day. Assuming 10000 pods (probably 5000-8000 deployments), this is ~360 MB per day, or 2.5 GB per week.

By default, this data is retained for 60 days, afterward it is deleted. This correlates to around 20 to 25 GB of storage.

A query ID is generated for each data query operation, such that all data points for a single query can be grouped together.

By default, this information on gathered ten minute intervals. This interval can be configured. Furthermore, regardless of chosen interval, the query windows are always aligned to the beginning of each hour. Hence only  query intervals which evenly divide 60 are valid.

Currently, two commands can be used to gather this data: `mothership metering sync` and `mothership metering backfill`

### Continuous Sync
`mothership metering sync` can be used to indefinetely query kubecost and sync data to the fine grained metering table in Aurora, querying every ten minutes by default.

### Backfill
`mothership metering backfill` can be used to backfill data for a given time range. This command will query kubecost for the given time range, and selectively backfill data for time intervals that are not present in the fine grained metering table. A start and end time can be specified. By default, the command will backfill data from the most recent query stored in the fine grained metering table to the current time.

### Deployment
Fine grained data should ideally be gathered continuously using `sync`. In the event of lost data, `backfill` can be used to selectively backfill missing data. If prometheus goes down, the data during that window generally will not be recoverable.

As these commands interact with kubecost, deploying and running in-cluster is preferred. `sync` can exist as a continuously running deployment, while `backfill` can be run as a cronjob once or twice a day. Thus in the event of sync failures, data can be recovered using backfill.

todo: a third deployment that constantly checks for missing data and runs backfill as necessary. This will minimize inaccuracies in the event of sync failures. Another option could be to run `backfill` before we run `aggregate` for redundancy purposes.


## Compute Aggregation
Aggregated data is stored in three tables, corresponding to hourly, daily, and weekly usage.
The schema for hourly data is as follows:
```
"workspace_id"   text not null default '',
"deployment_name" text not null default '',
"shape"   text   not null default '',
"end_time"    timestamp with time zone default now(),
"usage"   bigint not null,
"batch_id" uuid not null,
"stripe_usage_record_id" text null default 'NULL'::text,
primary key (workspace_id, deployment_name, shape, end_time)
```

The daily and weekly tables are the same, but without a `deployment_name` column.

These tables are defined as `MeteringTableComputeHourly`, `MeteringTableComputeDaily`, and `MeteringTableComputeWeekly`.

The `aggregate` command will aggregate data from the fine grained table into the hourly, daily, and weekly tables. A start time must be specified. By default, `aggregate` truncates this start time to the nearest hour,day, or week, and aggregates exactly one unit of time into the corresponding table. A `batch_id` is computed from the primary key and is mostly used for debugging purposes.
Two copies of this table exist: one stored with aurora, and another stored with supabase. The `stripe_usage_record_id` is only present on the supabase table.

Currently there is no "daemon" for aggregation, thus we must schedule a job to run `mothership metering aggregate` once every hour/day/week. This does not need to be run in cluster as it does not interact with kubecost, and only with the database clients. We could probably deploy this in the mothership cluster.

In general `aggregate` failure is not a serious issue. The most likely failures/issues can stem from incomplete fine_grain data, and from read/write issues involving the db connection.

* Incomplete fine grain data: if initial results of `aggregate` are inaccurate due to missing/inaccurate/duplicate fine grain data, once the fine grain data has been rectified, `aggregate` can be run again to correct the aggregated tables (as we overwrite any existing rows for that specific primary key with the new `usage` value). While we check if fine grain data is incomplete for any aggregation window, there is no way to knowing if the data is accurate - we'll just have to trust kubecost.


* Read/write issues: `aggregate` may encounter errors where read/write transactions fail to either the aurora or supabase tables. Although all database operations performed have built-in retry mechanisms, these errors may still occur. Write transaction failures pose the largest threat as they may leave the aurora and supabase tables out of sync. However, as these are likely transient errors, 
* the general solution is to simply run `aggregate` again after a period of time. Since we use the primary key `(workspace_id, deployment_name, shape, end_time)` to de-dupe, we overwrite any existing 'incorrect' rows and re-insert any missing rows, but will not duplicate any 'correct' rows. 

Todo: automate failure re-scheduling for `aggregate` (using a crash backoff mechanism, waiting for db connection health, etc).


## Storage Usage Information
The following constants in `metering` package represent the efs storage data tables:
```
MeteringTableStorageFineGrain 
MeteringTableStorageHourly   
MeteringTableStorageDaily    
MeteringTableStorageWeekly
```

Raw storage data is stored using the following schema:
```
    batch_id uuid NOT NULL,
    workspace text NOT NULL,
    storage_id text not null,
    size_bytes bigint,
    end_time timestamptz not null default now(),
    primary key (batch_id, workspace, storage_id)
```
Unlike compute data, storage data is gathered at discrete points in time. Otherwise, it's structure is similar to compute data. `size_bytes` is the size of the storage volume at time end_time. For sync jobs run concurrently with compute data syncs, the `batch_id` will match that of the compute data.

## Storage Aggregation
```
    workspace_id text NOT NULL,
    storage_id text not null,
    size_bytes bigint,
    end_time timestamptz not null,
    batch_id uuid,
    primary key (workspace_id, storage_id, end_time)

```
`size_bytes` is the average size of the volume in the specified period of time (hourly, daily, or weekly). Furthermore, for aggregations run concurrently with compute data aggregations, the `batch_id` will match that of the compute data.

## Billing
Invoices are sent on stripe monthly, and usage is uploaded hourly. Furthermore, uploaded data cannot be modified after 24 hours, since Stripe expires its idempotency keys after 24 hours.

We currently have a webhook to automatically consume newly inserted rows and send them to stripe. Thus we need to coordinate our jobs so that all necessary `sync` and `backfill` operations are performed before running `aggregate`. In the case of inaccurate data reported to Stripe, any changes must be made within 24 hours of the initial Stripe upload.


## Notes
* TODO: implement cleaning tools to delete old data (i.e 60 day old data in fine grained tables)
