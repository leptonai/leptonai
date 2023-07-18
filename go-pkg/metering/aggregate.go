package metering

import (
	"database/sql"
	"fmt"
	"strings"
	"time"
)

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
)

type UsageAggregateRow struct {
	StartTime      time.Time
	EndTime        time.Time
	DeploymentName string
	Workspace      string
	Shape          string
	Usage          int
}

// GetUsageAggregate aggregates fine grain usage data for the specified hourly time window
func GetUsageAggregate(aurora AuroraDB, start, end time.Time) ([]UsageAggregateRow, error) {
	// check start and end times valid
	if start.IsZero() || end.IsZero() || start.Equal(end) || start.After(end) {
		return nil, fmt.Errorf("start time, end time invalid: %s | %s", start.Format(time.ANSIC), end.Format(time.ANSIC))
	}
	db := aurora.DB
	diff := end.Sub(start)
	switch diff {
	case time.Hour:
		return queryHourAgg(db, start, end)
	case time.Hour * 24, time.Hour * 168:
		return queryDailyOrWeeklyAgg(db, start, end)
	default:
		return nil, fmt.Errorf("time window does not match hourly, daily, or weekly: %s", diff.String())
	}
}

func queryHourAgg(db *sql.DB, start, end time.Time) ([]UsageAggregateRow, error) {
	rows, err := db.Query(fmt.Sprintf(`SELECT 
			namespace,
			shape,
			deployment_name,
			ROUND(SUM(minutes)) as usage
			from %s
			where query_start >= '%s' and query_end <= '%s'
			GROUP BY namespace, deployment_name, shape`,
		MeteringTableFineGrain,
		start.Format(time.RFC3339),
		end.Format(time.RFC3339),
	))
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var res []UsageAggregateRow
	for rows.Next() {
		var agg UsageAggregateRow
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

func queryDailyOrWeeklyAgg(db *sql.DB, start, end time.Time) ([]UsageAggregateRow, error) {
	rows, err := db.Query(fmt.Sprintf(`SELECT
			namespace,
			shape,
			ROUND(SUM(minutes)) as usage
			from %s
			where query_start >= '%s' and query_end <= '%s'
			GROUP BY namespace, shape`,
		MeteringTableFineGrain,
		start.Format(time.RFC3339),
		end.Format(time.RFC3339),
	))
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var res []UsageAggregateRow
	for rows.Next() {
		var agg UsageAggregateRow
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

func InsertRowsIntoAggregate(tx *sql.Tx, tableName MeteringTable, aggregateData []UsageAggregateRow, batch_id string) (int64, error) {
	var cmd string
	var onConflict string
	var rowStr string

	switch tableName {
	case MeteringTableHourly:
		cmd = fmt.Sprintf(insertHourly, tableName)
		onConflict = insertHourlyOnConflict
		rowStr = genRowStr(6)
	case MeteringTableDaily, MeteringTableWeekly:
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
		case MeteringTableHourly:
			vals = append(vals, batch_id, r.EndTime, r.Workspace, r.DeploymentName, r.Shape, r.Usage)
		case MeteringTableDaily, MeteringTableWeekly:
			vals = append(vals, batch_id, r.EndTime, r.Workspace, r.Shape, r.Usage)
		}
	}
	sqlStr := cmd + strings.Join(toInsert, ",") + onConflict
	sqlStr = replaceSQL(sqlStr, "?")

	stmt, _ := tx.Prepare(sqlStr)
	defer stmt.Close()
	res, err := stmt.Exec(vals...)
	if err != nil {
		return 0, err
	}
	affected, err := res.RowsAffected()
	if err != nil {
		return 0, err
	}
	return affected, nil
}
