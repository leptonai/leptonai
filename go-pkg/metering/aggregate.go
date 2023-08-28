package metering

import (
	"database/sql"
	"fmt"
	"time"
)

type ComputeAggregateRow struct {
	StartTime      time.Time
	EndTime        time.Time
	DeploymentName string
	Workspace      string
	Shape          string
	Usage          int
}

type StorageAggregateRow struct {
	StartTime time.Time
	EndTime   time.Time
	Workspace string
	// storageID corresponds to the FilesystemID returned by the EFS API
	storageID string
	sizeBytes uint64
}

const (
	updateLastUsedTimestamp = `UPDATE workspaces SET last_billable_usage_timestamp = '%s' WHERE id = '%s'`

	insertHourly = `INSERT INTO %s (
		batch_id,
		end_time,
		workspace_id,
		deployment_name,
		shape,
		usage
	)
	VALUES `
	/*
		(end_time, workspace_id, deployment_name, shape) is the composite primary key
		on conflict prevents pq from throwing primary key errors when running the same query twice
		set usage will update the usage column to the more recent queried value
		should be the same as the previous value, given that previous value was calculated after all relevant fine_grain data was synced
	*/
	insertHourlyOnConflict = ` ON CONFLICT (end_time, workspace_id, deployment_name, shape) DO UPDATE SET usage = excluded.usage`

	insertDailyOrWeekly = `INSERT INTO %s (
		batch_id,
		end_time,
		workspace_id,
		shape,
		usage
	)
	VALUES `
	insertDailyOrWeeklyOnConflict = ` ON CONFLICT (workspace_id, shape, end_time) DO UPDATE SET usage = excluded.usage`

	insertStorage = `INSERT INTO %s (
		batch_id,
		end_time,
		workspace_id,
		storage_id,
		size_bytes,
		size_gb
	)
	VALUES `
	insertStorageOnConflict = ` ON CONFLICT (end_time, workspace_id, storage_id) DO UPDATE SET size_bytes = excluded.size_bytes, size_gb = excluded.size_gb`
	bytesInGibabyte         = 1000000000
)

// GetComputeAggregate aggregates fine grain usage data for the specified hourly time window
func GetComputeAggregate(aurora AuroraDB, cluster string, start, end time.Time) ([]ComputeAggregateRow, error) {
	// check start and end times valid
	if start.IsZero() || end.IsZero() || start.Equal(end) || start.After(end) {
		return nil, fmt.Errorf("start time, end time invalid: %s | %s", start.Format(time.ANSIC), end.Format(time.ANSIC))
	}
	db := aurora.DB
	diff := end.Sub(start)
	switch diff {
	case time.Hour:
		return queryHourlyComputeAgg(db, cluster, start, end)
	case time.Hour * 24, time.Hour * 168:
		return queryDailyOrWeeklyComputeAgg(db, cluster, start, end)
	default:
		return nil, fmt.Errorf("time window does not match hourly, daily, or weekly: %s", diff.String())
	}
}

func queryHourlyComputeAgg(db *sql.DB, cluster string, start, end time.Time) ([]ComputeAggregateRow, error) {
	// all user workspaces are prefixed with 'ws-'
	// REGEXP_REPLACE removes 'ws-' prefix from workspaces
	// LENGTH(deployment_name) > 0 filters out pods not associated with a lepton deployment
	rows, err := db.Query(fmt.Sprintf(`SELECT 
			REGEXP_REPLACE(namespace, '^ws-', '') as namespace,
			shape,
			deployment_name,
			ROUND(SUM(minutes)) as usage
			from %s
			where cluster='%s' and
			query_start >= '%s' and query_end <= '%s' 
			and namespace ilike 'ws-%%'
			and LENGTH(deployment_name) > 0
			GROUP BY namespace, deployment_name, shape`,
		MeteringTableComputeFineGrain,
		cluster,
		start.Format(time.RFC3339),
		end.Format(time.RFC3339),
	))
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var res []ComputeAggregateRow
	for rows.Next() {
		var agg ComputeAggregateRow
		agg.StartTime = start
		agg.EndTime = end
		err := rows.Scan(&agg.Workspace, &agg.Shape, &agg.DeploymentName, &agg.Usage)
		if err != nil {
			return nil, err
		}
		res = append(res, agg)
	}
	return res, nil
}

func queryDailyOrWeeklyComputeAgg(db *sql.DB, cluster string, start, end time.Time) ([]ComputeAggregateRow, error) {
	// all user workspaces are prefixed with 'ws-'
	// REGEXP_REPLACE removes 'ws-' prefix from workspaces
	// LENGTH(deployment_name) > 0 filters out pods not associated with a lepton deployment
	rows, err := db.Query(fmt.Sprintf(`SELECT
			REGEXP_REPLACE(namespace, '^ws-', '') as namespace,
			shape,
			ROUND(SUM(minutes)) as usage
			from %s
			where cluster='%s' and
			query_start >= '%s' and query_end <= '%s'
			and namespace ilike 'ws-%%'
			and LENGTH(deployment_name) > 0
			GROUP BY namespace, shape`,
		MeteringTableComputeFineGrain,
		cluster,
		start.Format(time.RFC3339),
		end.Format(time.RFC3339),
	))
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var res []ComputeAggregateRow
	for rows.Next() {
		var agg ComputeAggregateRow
		agg.StartTime = start
		agg.EndTime = end
		err := rows.Scan(&agg.Workspace, &agg.Shape, &agg.Usage)
		if err != nil {
			return nil, err
		}
		res = append(res, agg)
	}
	return res, nil
}

func InsertRowsIntoComputeAggregate(tx *sql.Tx, tableName MeteringTable, aggregateData []ComputeAggregateRow, batchID string) (int64, error) {
	var cmd string
	var onConflict string
	var rowStr string

	switch tableName {
	case MeteringTableComputeHourly:
		cmd = fmt.Sprintf(insertHourly, tableName)
		onConflict = insertHourlyOnConflict
		rowStr = genRowStr(6)
	case MeteringTableComputeDaily, MeteringTableComputeWeekly:
		cmd = fmt.Sprintf(insertDailyOrWeekly, tableName)
		onConflict = insertDailyOrWeeklyOnConflict
		rowStr = genRowStr(5)
	default:
		return 0, fmt.Errorf("invalid table name: %s", tableName)
	}
	var toInsert []string
	var vals []interface{}
	affected := int64(0)
	for _, d := range aggregateData {
		toInsert = append(toInsert, rowStr)
		switch tableName {
		case MeteringTableComputeHourly:
			vals = append(vals, batchID, d.EndTime, d.Workspace, d.DeploymentName, d.Shape, d.Usage)
		case MeteringTableComputeDaily, MeteringTableComputeWeekly:
			vals = append(vals, batchID, d.EndTime, d.Workspace, d.Shape, d.Usage)
		}
		if len(toInsert) >= insertBatchSize {
			res, err := sqlInsert(tx, cmd, toInsert, onConflict, vals)
			if err != nil {
				return 0, err
			}
			batchAffected, err := res.RowsAffected()
			if err != nil {
				return 0, err
			}
			affected += batchAffected
			toInsert = []string{}
			vals = []interface{}{}
		}
	}
	if len(toInsert) > 0 {
		res, err := sqlInsert(tx, cmd, toInsert, onConflict, vals)
		if err != nil {
			return 0, err
		}
		batchAffected, err := res.RowsAffected()
		if err != nil {
			return 0, err
		}
		affected += batchAffected
	}
	return affected, nil
}

func GetStorageAggregate(aurora AuroraDB, start, end time.Time) ([]StorageAggregateRow, error) {
	if start.IsZero() || end.IsZero() || start.Equal(end) || start.After(end) {
		return nil, fmt.Errorf("start time, end time invalid: %s | %s", start.Format(time.ANSIC), end.Format(time.ANSIC))
	}
	db := aurora.DB
	diff := end.Sub(start)
	if !(diff == time.Hour || diff == time.Hour*24 || diff == time.Hour*168) {
		return nil, fmt.Errorf("time window does not match hourly, daily, or weekly: %s", diff.String())
	}
	return queryStorageAgg(db, start, end)
}

func queryStorageAgg(db *sql.DB, start, end time.Time) ([]StorageAggregateRow, error) {
	rows, err := db.Query(fmt.Sprintf(`SELECT
            workspace, storage_id, ROUND(AVG(size_bytes)) as avg_size
            from %s
            where time > '%s' and time <= '%s'
            GROUP BY workspace, storage_id`,
		MeteringTableStorageFineGrain,
		start.Format(time.RFC3339),
		end.Format(time.RFC3339),
	))
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var res []StorageAggregateRow
	for rows.Next() {
		var agg StorageAggregateRow
		agg.StartTime = start
		agg.EndTime = end
		err := rows.Scan(&agg.Workspace, &agg.storageID, &agg.sizeBytes)
		if err != nil {
			return nil, err
		}
		res = append(res, agg)
	}
	return res, nil
}

// updates the `workspace` table in the supabase 'public' schema with the last used timestamp for the workspace
func UpdateWorkspacesLastUsedTimestamp(supabaseDB *sql.DB, computeData []ComputeAggregateRow, storageData []StorageAggregateRow, timestamp time.Time) (int64, error) {
	// find all unique workspace ids from compute and storage data
	var workspaces = map[string]bool{}
	for _, d := range computeData {
		// only want workspaces with at least 1 minute of usage
		if d.Usage > 0 {
			workspaces[d.Workspace] = true
		}
	}
	for _, d := range storageData {
		// only want workspaces with storage usage > 1GB
		if d.sizeBytes > bytesInGibabyte {
			workspaces[d.Workspace] = true
		}
	}

	tx, err := supabaseDB.Begin()
	if err != nil {
		return 0, err
	}

	// update last used timestamp for each workspace
	totalAffected := int64(0)
	for ws := range workspaces {
		res, err := tx.Exec(fmt.Sprintf(updateLastUsedTimestamp, timestamp.Format(time.RFC3339), ws))
		if err != nil {
			return 0, err
		}
		affected, err := res.RowsAffected()
		if err != nil {
			return 0, err
		}
		totalAffected += affected
	}

	err = tx.Commit()
	if err != nil {
		rollbackErr := tx.Rollback()
		if rollbackErr != nil {
			return 0, fmt.Errorf("failed to commit UpdateWorkspacesLastUsedTimestamp txn, error: %v, rollback error: %v", err, rollbackErr)
		}
		return 0, fmt.Errorf("failed to commit UpdateWorkspacesLastUsedTimestamp txn: %v", err)
	}
	return totalAffected, nil
}
func InsertRowsIntoStorageAggregate(tx *sql.Tx, tableName MeteringTable, aggregateData []StorageAggregateRow, batchID string) (int64, error) {
	if !(tableName == MeteringTableStorageHourly || tableName == MeteringTableStorageDaily || tableName == MeteringTableStorageWeekly) {
		return 0, fmt.Errorf("invalid table name: %s", tableName)
	}

	cmd := fmt.Sprintf(insertStorage, tableName)
	onConflict := insertStorageOnConflict
	rowStr := genRowStr(6)
	var toInsert []string
	var vals []interface{}
	affected := int64(0)
	for _, d := range aggregateData {
		toInsert = append(toInsert, rowStr)
		// gets the floor of size in GB
		sizeGB := int(d.sizeBytes / bytesInGibabyte)
		vals = append(vals, batchID, d.EndTime.UTC(), d.Workspace, d.storageID, d.sizeBytes, sizeGB)
		if len(toInsert) >= insertBatchSize {
			res, err := sqlInsert(tx, cmd, toInsert, onConflict, vals)
			if err != nil {
				return 0, err
			}
			batchAffected, err := res.RowsAffected()
			if err != nil {
				return 0, err
			}
			affected += batchAffected
			toInsert = []string{}
			vals = []interface{}{}
		}
	}
	if len(toInsert) > 0 {
		res, err := sqlInsert(tx, cmd, toInsert, onConflict, vals)
		if err != nil {
			return 0, err
		}
		batchAffected, err := res.RowsAffected()
		if err != nil {
			return 0, err
		}
		affected += batchAffected
	}
	return affected, nil
}
