package aggregate

import (
	"crypto/md5"
	"database/sql"
	"fmt"
	"log"
	"time"

	"github.com/leptonai/lepton/go-pkg/metering"
	"github.com/leptonai/lepton/go-pkg/supabase"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"

	"github.com/araddon/dateparse"
	"github.com/spf13/cobra"
)

var (
	startTimeFlag    string
	endTimeFlag      string
	tableFlag        string
	supabasePassword string
)

func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "aggregate",
		Short: "Aggregate all data from start-time to end-time, into the specified aggregate table",
		Long: `
# Aggregate data from start-time to end-time, into the specified aggregate table.
--start-time value must be provided
--end-time is optional and will default a single unit of aggregation after the start-time.
--table value must be provided, and one of 'hourly', 'daily', or 'weekly'.

Both start and end times will be truncated down to the nearest whole unit of aggregation.
E.G:

hourly aggregation: '2023-07-11T20:40:00+00' -> '2023-07-11T20:00:00+00'
daily aggregation: '2023-07-11T20:40:00+00' -> '2023-07-11T00:00:00+00'
weekly aggregation: '2023-07-11T20:40:00+00' -> '2023-07-10T00:00:00+00'
This is to ensure that no aggregation overlap occurs.


Weekly aggregation starts from Monday 12AM, and ends on Sunday 11:59:59PM.
Daily aggregation starts from 12AM, and ends on 11:59:59PM.

Usage examples:
To aggregate a single hour of data starting from 8 PM UTC time, on July 11th, 2023, into the hourly table:
mothership metering aggregate --start-time "2023-07-11T20:40:00+00" --table hourly

The minutes and seconds are ignored, so, this is the same as:
mothership metering aggregate --start-time "2023-07-11T20:00:00+00" --table hourly

we can also use human readable time formats:
mothership metering aggregate --start-time "7/11/2023 8:00PM" --table hourly

Note that the following 3 commands are equivalent
To aggregate July 11th and July 12th data into the daily table: 
mothership metering aggregate --start-time "2023-07-11T00:00:00+00" --end-time "2023-07-13T00:00:00+00" --table daily
mothership metering aggregate --start-time "07/11/2023 12:30 AM" --end-time "07/11/2023 8:30 PM" --table daily
mothership metering aggregate --start-time "07/11/2023M" --end-time "07-13" --table daily
mothership metering aggregate --start-time 1689033600 --end-time 1689206400 --table daily
`,

		Run: aggregateFunc,
	}

	cmd.PersistentFlags().StringVarP(&startTimeFlag, "start-time", "s", "", "start time to aggregate from")
	cmd.PersistentFlags().StringVarP(&endTimeFlag, "end-time", "e", "", "end time to aggregate to")
	cmd.PersistentFlags().StringVarP(&tableFlag, "table", "t", "hourly", "table to aggregate to, accepts 'hourly', 'daily', 'weekly'")
	cmd.PersistentFlags().StringVarP(&supabasePassword, "supabase-password", "p", "", "supabase password, can also be passed in using env var SUPABASE_PASSWORD")
	return cmd
}

func aggregateFunc(cmd *cobra.Command, args []string) {
	// TODO: add daily and weekly tables.
	if tableFlag != "hourly" {
		log.Fatal("only --table 'hourly' supported for now", tableFlag)
	}

	// create aurora connection
	auroraCfg := common.ReadAuroraConfigFromFlag(cmd)
	db, err := auroraCfg.NewHandler()
	if err != nil {
		log.Fatalf("couldn't connect to aurora db: %v", err)
	}
	aurora := metering.AuroraDB{DB: db}
	defer aurora.DB.Close()
	// create supabase connection
	supabaseConfig := supabase.NewDefaultConfigFromFlagAndEnv(supabasePassword)
	supabaseDB, err := supabaseConfig.NewHandler()
	if err != nil {
		log.Fatalf("couldn't connect to supabase db: %v", err)
	}
	defer supabaseDB.Close()

	var queryInterval time.Duration
	switch tableFlag {
	case "hourly":
		queryInterval = time.Hour
	case "daily":
		queryInterval = 24 * time.Hour
	case "weekly":
		queryInterval = 168 * time.Hour
	default:
		log.Fatalf(`invalid table %s, must be one of ("hourly", "daily", "weekly")`, tableFlag)
	}
	// get start and end times
	var startTime, endTime time.Time
	if len(startTimeFlag) <= 0 {
		log.Fatal("No --start-time passed, and could not get most recent fine_grain entry")
	} else {
		var err error
		startTime, err = dateparse.ParseAny(startTimeFlag)
		if err != nil {
			log.Fatal("couldn't parse --start-time: ", err)
		}
	}
	if len(endTimeFlag) <= 0 {
		log.Println("no end time specified, defaulting to one unit of aggregation after start time")
		endTime = startTime.Add(queryInterval)
	} else {
		var err error
		if endTimeFlag == "now" {
			endTime = time.Now().UTC()
		} else {
			endTime, err = dateparse.ParseAny(endTimeFlag)
			if err != nil {
				log.Fatal("couldn't parse --end-time: ", err)
			}
		}
	}
	// truncate start and end times to the nearest whole unit of aggregation
	startTime, endTime = startTime.Truncate(queryInterval), endTime.Truncate(queryInterval)
	// compare start and end times to the most recent fine grain entry
	_, lastQueryEnd, err := metering.GetMostRecentFineGrainEntry(aurora)
	if err != nil {
		log.Fatalf("couldn't get most recent fine grain entry: %v", err)
	}
	if startTime.After(lastQueryEnd) {
		log.Fatalf("Invalid start time: %v is after the most recent fine grain query%v", startTime.Format(time.RFC3339), lastQueryEnd)
	}
	if lastQueryEnd.Before(endTime) {
		log.Printf("Warning: end time %s is past the most recent fine grain query %s. This aggregation will be incomplete.",
			endTime.Format(time.RFC3339), lastQueryEnd.Format(time.RFC3339))
	}
	// get all intermediate query windows, aggregate each one and write to DB
	// TODO: execute in one query
	startTimes, endTimes := getIntermediateQueryWindows(startTime, endTime, queryInterval)
	for i := 0; i < len(startTimes); i++ {
		var aggregate []metering.UsageAggregateRow
		aggregate, err = metering.GetUsageAggregate(aurora, startTimes[i], endTimes[i])
		if err != nil {
			log.Fatalf("couldn't get %s aggregate data for window %s - %s: %v",
				tableFlag, startTime.Format(time.RFC3339), endTime.Format(time.RFC3339), err)
		}
		// create a 128 bit md5 batch_id for this aggregation
		hash := md5.New()
		hash.Write([]byte(fmt.Sprintf("%d%d%d", startTimes[i].Unix(), endTimes[i].Unix()*10, len(aggregate)*100)))
		hashSum := hash.Sum(nil)
		batchID := fmt.Sprintf("%x", hashSum)

		// TODO: add daily and weekly tables
		switch tableFlag {
		case "hourly":
			maxRetries := 10
			_, err = retryInsertIntoHourly(aurora.DB, metering.MeteringTableAuroraHourly, maxRetries, aggregate, batchID)
			if err != nil {
				log.Fatalf("couldn't insert into aurora hourly table: %v", err)
			}
			_, err = retryInsertIntoHourly(supabaseDB, metering.MeteringTableSupabaseHourly, maxRetries, aggregate, batchID)
			if err != nil {
				log.Fatalf("couldn't insert into supabase hourly table: %v", err)
			}
		case "daily":
			log.Fatal("daily table not yet supported")
		case "weekly":
			log.Fatal("weekly table not yet supported")
		default:
			log.Fatalf(`invalid table %s, must be one of ("hourly", "daily", "weekly")`, tableFlag)
		}
	}
	log.Printf("successfully processed %s aggregate data for window (%s,%s)", tableFlag, startTime.Format(time.RFC3339), endTime.Format(time.RFC3339))
}

func retryInsertIntoHourly(db *sql.DB, table metering.MeteringTable, maxRetries int, aggregate []metering.UsageAggregateRow, batch_id string) (int64, error) {
	for retries := 0; retries < maxRetries; retries++ {
		tx, err := db.Begin()
		if err != nil {
			log.Printf("couldn't begin transaction: %v", err)
			continue
		}
		rows, err := metering.InsertRowsIntoHourly(tx, table, aggregate, batch_id)
		if err != nil {
			log.Printf("failed to execute query, trying again %v", err)
			err = tx.Rollback()
			if err != nil {
				log.Printf("failed to rollback transaction: %v", err)
				continue
			}
			continue
		}

		err = tx.Commit()
		if err != nil {
			log.Printf("failed to commit transaction, trying again %v", err)
			err = tx.Rollback()
			if err != nil {
				log.Printf("failed to rollback transaction: %v", err)
				continue
			}
			continue
		}
		return rows, nil
	}
	return 0, fmt.Errorf("failed to insert rows into hourly table after %d retries", maxRetries)
}

// get intermediate start and end times, interval time apart, between queryStart and queryEnd
func getIntermediateQueryWindows(queryStart, queryEnd time.Time, interval time.Duration) ([]time.Time, []time.Time) {
	var startTimes []time.Time
	var EndTimes []time.Time
	for t := queryStart; t.Before(queryEnd); t = t.Add(interval) {
		startTimes = append(startTimes, t)
		EndTimes = append(EndTimes, t.Add(interval))
	}
	if len(startTimes) != len(EndTimes) {
		log.Fatalf("%d start times generated but %d end times generated", len(startTimes), len(EndTimes))
	}
	return startTimes, EndTimes
}
