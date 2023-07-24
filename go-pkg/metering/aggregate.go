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
		size_bytes
	)
	VALUES `
	insertStorageOnConflict = ` ON CONFLICT (end_time, workspace_id, storage_id) DO UPDATE SET size_bytes = excluded.size_bytes`
)

// GetUsageAggregate aggregates fine grain usage data for the specified hourly time window
func GetComputeAggregate(aurora AuroraDB, start, end time.Time) ([]ComputeAggregateRow, error) {
	// check start and end times valid
	if start.IsZero() || end.IsZero() || start.Equal(end) || start.After(end) {
		return nil, fmt.Errorf("start time, end time invalid: %s | %s", start.Format(time.ANSIC), end.Format(time.ANSIC))
	}
	db := aurora.DB
	diff := end.Sub(start)
	switch diff {
	case time.Hour:
		return queryHourComputeAgg(db, start, end)
	case time.Hour * 24, time.Hour * 168:
		return queryDailyOrWeeklyComputeAgg(db, start, end)
	default:
		return nil, fmt.Errorf("time window does not match hourly, daily, or weekly: %s", diff.String())
	}
}

func queryHourComputeAgg(db *sql.DB, start, end time.Time) ([]ComputeAggregateRow, error) {
	rows, err := db.Query(fmt.Sprintf(`SELECT 
			namespace,
			shape,
			deployment_name,
			ROUND(SUM(minutes)) as usage
			from %s
			where query_start >= '%s' and query_end <= '%s'
			GROUP BY namespace, deployment_name, shape`,
		MeteringTableComputeFineGrain,
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

func queryDailyOrWeeklyComputeAgg(db *sql.DB, start, end time.Time) ([]ComputeAggregateRow, error) {
	rows, err := db.Query(fmt.Sprintf(`SELECT
			namespace,
			shape,
			ROUND(SUM(minutes)) as usage
			from %s
			where query_start >= '%s' and query_end <= '%s'
			GROUP BY namespace, shape`,
		MeteringTableComputeFineGrain,
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

func InsertRowsIntoComputeAggregate(tx *sql.Tx, tableName MeteringTable, aggregateData []ComputeAggregateRow, batch_id string) (int64, error) {
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
	for _, r := range aggregateData {
		toInsert = append(toInsert, rowStr)
		switch tableName {
		case MeteringTableComputeHourly:
			vals = append(vals, batch_id, r.EndTime, r.Workspace, r.DeploymentName, r.Shape, r.Usage)
		case MeteringTableComputeDaily, MeteringTableComputeWeekly:
			vals = append(vals, batch_id, r.EndTime, r.Workspace, r.Shape, r.Usage)
		}
	}
	res, err := sqlInsert(tx, cmd, toInsert, onConflict, vals)
	if err != nil {
		return 0, err
	}
	affected, err := res.RowsAffected()
	if err != nil {
		return 0, err
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

func InsertRowsIntoStorageAggregate(tx *sql.Tx, tableName MeteringTable, aggregateData []StorageAggregateRow, batch_id string) (int64, error) {
	if !(tableName == MeteringTableStorageHourly || tableName == MeteringTableStorageDaily || tableName == MeteringTableStorageWeekly) {
		return 0, fmt.Errorf("invalid table name: %s", tableName)
	}

	cmd := fmt.Sprintf(insertStorage, tableName)
	onConflict := insertStorageOnConflict
	rowStr := genRowStr(5)
	var toInsert []string
	var vals []interface{}
	for _, r := range aggregateData {
		toInsert = append(toInsert, rowStr)
		vals = append(vals, batch_id, r.EndTime.UTC(), r.Workspace, r.storageID, r.sizeBytes)
	}

	res, err := sqlInsert(tx, cmd, toInsert, onConflict, vals)
	if err != nil {
		return 0, err
	}
	affected, err := res.RowsAffected()
	if err != nil {
		return 0, err
	}
	return affected, nil
}
