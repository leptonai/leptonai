package aggregate

import (
	"database/sql"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/google/uuid"
	"github.com/leptonai/lepton/go-pkg/metering"
	"github.com/leptonai/lepton/go-pkg/supabase"
	"github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"

	"github.com/araddon/dateparse"
	"github.com/spf13/cobra"
)

var (
	startTimeFlag    string
	endTimeFlag      string
	tableFlag        string
	supabasePassword string
	enableCompute    bool
	enableStorage    bool

	runBackground   bool
	runBackgroundOn int
)

func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "aggregate",
		Short: "Aggregate all data from start-time to end-time, into the specified aggregate table",
		Long: `
# Aggregate data from start-time to end-time, into the specified aggregate table.
--run-background will run hourly aggregation indefinitely. This ignores --start-time, --end-time, --table flags.
--end-time is optional, and defaults to the current time.
--start-time value is optional, and defaults to one unit of aggregation before --end-time.
--table value must be provided if not running in background, and one of 'hourly', 'daily', or 'weekly'.

--enable-compute is optional, defaults to false. If true, will enable aggregation of compute (CPU, GPU, RAM) data.
--enable-storage is optional, defaults to false. If true, will enable aggregation of storage (EFS) data.

Both start and end times will be truncated down to the nearest whole unit of aggregation.
Weekly aggregation starts from Monday 12AM, and ends on Sunday 11:59:59PM.
Daily aggregation starts from 12AM, and ends on 11:59:59PM.
Thus the following are equivalent:

hourly aggregation: '2023-07-11T20:40:00+00' -> '2023-07-11T20:00:00+00'
daily aggregation: '2023-07-11T20:40:00+00' -> '2023-07-11T00:00:00+00'
weekly aggregation: '2023-07-11T20:40:00+00' -> '2023-07-10T00:00:00+00'

Usage examples:
To aggregate a single hour of data from 8-9 PM UTC time, on July 11th, 2023, into the hourly table:
mothership metering aggregate --end-time "2023-07-11T21:40:00+00" --table hourly

The minutes and seconds are ignored, so, this is the same as:
mothership metering aggregate --end-time "2023-07-11T21:00:00+00" --table hourly

we can also use human readable time formats (ref https://github.com/araddon/dateparse):
mothership metering aggregate --start-time "7/11/2023 8:00PM" --table hourly
`,

		Run: aggregateFunc,
	}

	cmd.PersistentFlags().StringVarP(&startTimeFlag, "start-time", "s", "", "start time to aggregate from")
	cmd.PersistentFlags().StringVarP(&endTimeFlag, "end-time", "e", "", "end time to aggregate to")
	cmd.PersistentFlags().StringVarP(&tableFlag, "table", "t", "hourly", "table to aggregate to, accepts 'hourly', 'daily', 'weekly'")
	cmd.PersistentFlags().StringVarP(&supabasePassword, "supabase-password", "p", "", "supabase password, can also be passed in using env var SUPABASE_PASSWORD")

	cmd.PersistentFlags().BoolVar(&enableCompute, "enable-compute", false, "enable aggregation of compute (CPU, GPU, RAM) data")
	cmd.PersistentFlags().BoolVar(&enableStorage, "enable-storage", false, "enable aggregation of storage (EFS) data")

	cmd.PersistentFlags().BoolVar(&runBackground, "run-background", false, "run hourly aggregate in background indefinitely, ignoring --start-time, --end-time, --table flags")
	cmd.PersistentFlags().IntVar(&runBackgroundOn, "run-background-on", 5, "minute of hour to run aggregate each hour, must be between 0-59")
	return cmd
}

func aggregateFunc(cmd *cobra.Command, args []string) {
	if !(enableCompute || enableStorage) {
		log.Fatal("Neither storage nor compute aggregation enabled. Doing nothing.")
	}

	// create aurora connection
	auroraCfg := common.ReadAuroraConfigFromFlag(cmd)
	db, err := auroraCfg.NewHandler()
	if err != nil {
		log.Fatalf("couldn't connect to aurora db: %v", err)
	}
	aurora := metering.AuroraDB{DB: db}
	// create supabase connection
	supabaseConfig := supabase.NewDefaultConfigFromFlagAndEnv(supabasePassword)
	supabaseDB, err := supabaseConfig.NewHandler()
	if err != nil {
		log.Fatalf("couldn't connect to supabase db: %v", err)
	}
	defer aurora.DB.Close()
	defer supabaseDB.Close()

	if runBackground {
		if runBackgroundOn < 0 || runBackgroundOn > 59 {
			log.Fatalf("--run-background-on must be between 0-59, got %d", runBackgroundOn)
		}
		queryInterval := time.Hour
		sigs := make(chan os.Signal, 1)
		signal.Notify(sigs, syscall.SIGTERM, syscall.SIGINT)
		ticker := time.NewTicker(time.Minute)
		fmt.Printf("starting background aggregation on minute %d", runBackgroundOn)
		for range ticker.C {
			select {
			case <-sigs:
				ticker.Stop()
				return
			default:
				now := time.Now().UTC()
				currMinute := now.Minute()
				// run aggregation at runBackgroundOn minute of every hour
				if currMinute == runBackgroundOn {
					// recreate aurora connection
					auroraCfg := common.ReadAuroraConfigFromFlag(cmd)
					db, err := auroraCfg.NewHandler()
					if err != nil {
						log.Fatalf("couldn't connect to aurora db: %v", err)
					}
					aurora := metering.AuroraDB{DB: db}
					// recreate supabase connection
					supabaseConfig := supabase.NewDefaultConfigFromFlagAndEnv(supabasePassword)
					supabaseDB, err := supabaseConfig.NewHandler()
					if err != nil {
						log.Fatalf("couldn't connect to supabase db: %v", err)
					}

					startTime := now.Add(-queryInterval).Truncate(queryInterval)
					endTime := now.Truncate(queryInterval)
					log.Printf("Aggregating window (%s, %s) into hourly table. Compute enabled: %t, storage enabled: %t",
						startTime.Format(time.RFC3339), endTime.Format(time.RFC3339), enableCompute, enableStorage)
					batchID := uuid.New().String()
					aggregateOneWindowIntoTables(
						aurora,
						supabaseDB,
						startTime,
						endTime,
						"hourly",
						metering.MeteringTableComputeHourly,
						metering.MeteringTableStorageHourly,
						batchID,
						5,
					)
					log.Printf("successfully processed %s aggregate data for window (%s,%s)", tableFlag, startTime.Format(time.RFC3339), endTime.Format(time.RFC3339))
					err = aurora.DB.Close()
					if err != nil {
						log.Printf("couldn't close aurora db connection: %v", err)
					}
					err = supabaseDB.Close()
					if err != nil {
						log.Printf("couldn't close supabase db connection: %v", err)
					}
				} else {
					timeToNext := runBackgroundOn - currMinute
					if currMinute >= runBackgroundOn {
						timeToNext += 60
					}
					log.Printf("next aggregate operation in %d minutes", timeToNext)
				}
			}
		}
	}

	var queryInterval time.Duration
	var computeTable metering.MeteringTable
	var storageTable metering.MeteringTable
	switch tableFlag {
	case "hourly":
		queryInterval = time.Hour
		computeTable = metering.MeteringTableComputeHourly
		storageTable = metering.MeteringTableStorageHourly
	case "daily":
		queryInterval = 24 * time.Hour
		computeTable = metering.MeteringTableComputeDaily
		storageTable = metering.MeteringTableStorageHourly
	case "weekly":
		queryInterval = 168 * time.Hour
		computeTable = metering.MeteringTableComputeWeekly
		storageTable = metering.MeteringTableStorageHourly
	default:
		log.Fatalf(`invalid table %s, must be one of ("hourly", "daily", "weekly")`, tableFlag)
	}

	// get start and end times
	var startTime, endTime time.Time
	if len(endTimeFlag) <= 0 {
		log.Println("no end time specified, defaulting to current time")
		endTime = time.Now().UTC()
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
	if len(startTimeFlag) <= 0 {
		// default to one unit of aggregation before end time
		log.Println("no start time specified, defaulting to one unit of aggregation before end time")
		startTime = endTime.Add(-queryInterval)
	} else {
		var err error
		startTime, err = dateparse.ParseAny(startTimeFlag)
		if err != nil {
			log.Fatal("couldn't parse --start-time: ", err)
		}
		if startTime.After(endTime) {
			log.Fatalf("provided start-time %s is after end-time %s", startTime.Format(time.RFC3339), endTime.Format(time.RFC3339))
		}
	}
	// truncate start and end times to the nearest whole unit of aggregation
	startTime, endTime = startTime.Truncate(queryInterval), endTime.Truncate(queryInterval)
	log.Printf("Aggregating window (%s, %s) into %s table. Compute enabled: %t, storage enabled: %t",
		startTime.Format(time.RFC3339), endTime.Format(time.RFC3339), tableFlag, enableCompute, enableStorage)

	// compare start and end times to the most recent fine grain entries
	if enableCompute {
		_, lastQueryEnd, err := metering.GetMostRecentFineGrainEntry(aurora, metering.MeteringTableComputeFineGrain)
		if err != nil {
			log.Fatalf("couldn't get most recent compute data fine grain entry: %v", err)
		}
		if startTime.After(lastQueryEnd) {
			log.Fatalf("Invalid start time: %v is after the most recent compute data fine grain query%v", startTime.Format(time.RFC3339), lastQueryEnd)
		}
		if lastQueryEnd.Before(endTime) {
			log.Printf("Warning: end time %s is past the most recent compute data fine grain query %s. This aggregation will be incomplete.",
				endTime.Format(time.RFC3339), lastQueryEnd.Format(time.RFC3339))
		}
	}
	if enableStorage {
		_, lastQueryEnd, err := metering.GetMostRecentFineGrainEntry(aurora, metering.MeteringTableStorageFineGrain)
		if err != nil {
			log.Fatalf("couldn't get most recent storage data fine grain entry: %v", err)
		}
		if startTime.After(lastQueryEnd) {
			log.Fatalf("Invalid start time: %v is after the most recent storage fine grain query%v", startTime.Format(time.RFC3339), lastQueryEnd)
		}
		if lastQueryEnd.Before(endTime) {
			log.Printf("Warning: end time %s is past the most recent storage fine grain query %s. This aggregation will be incomplete.",
				endTime.Format(time.RFC3339), lastQueryEnd.Format(time.RFC3339))
		}
	}

	// get all intermediate query windows, aggregate each one and write to DB
	startTimes, endTimes := getIntermediateQueryWindows(startTime, endTime, queryInterval)
	maxRetries := 5
	for i := 0; i < len(startTimes); i++ {
		batchID := uuid.New().String()
		aggregateOneWindowIntoTables(
			aurora,
			supabaseDB,
			startTimes[i],
			endTimes[i],
			tableFlag,
			computeTable,
			storageTable,
			batchID,
			maxRetries)
	}
	log.Printf("successfully processed %s aggregate data for window (%s,%s)", tableFlag, startTime.Format(time.RFC3339), endTime.Format(time.RFC3339))
}

// wrapper function for handling getting aggregate data and inserting into tables
func aggregateOneWindowIntoTables(
	aurora metering.AuroraDB,
	supabaseDB *sql.DB,
	startTime time.Time,
	endTime time.Time,
	tableFlag string,
	computeTable metering.MeteringTable,
	storageTable metering.MeteringTable,
	batchID string,
	maxRetries int,
) {
	if enableCompute {
		computeAggregate, err := metering.GetComputeAggregate(aurora, startTime, endTime)
		if err != nil {
			log.Fatalf("couldn't get %s aggregate data for window %s - %s: %v",
				tableFlag, startTime.Format(time.RFC3339), endTime.Format(time.RFC3339), err)
		}
		if len(computeAggregate) == 0 {
			log.Printf("no %s aggregate compute data for window %s - %s", tableFlag, startTime.Format(time.RFC3339), endTime.Format(time.RFC3339))
		} else {
			log.Printf("processing %d %s compute rows for window %s - %s", len(computeAggregate), tableFlag, startTime.Format(time.RFC3339), endTime.Format(time.RFC3339))

			_, err = retryInsertIntoComputeAggregate(aurora.DB, computeTable, computeAggregate, batchID, maxRetries)
			if err != nil {
				log.Fatalf("couldn't insert into aurora %s table: %v", tableFlag, err)
			}

			if computeTable == metering.MeteringTableComputeHourly {
				// insert into supabase table
				_, err = retryInsertIntoComputeAggregate(supabaseDB, computeTable, computeAggregate, batchID, maxRetries)
				if err != nil {
					log.Fatalf("couldn't insert into supabase %s table: %v", tableFlag, err)
				}
			}
		}
	}
	if enableStorage {
		storageAggregate, err := metering.GetStorageAggregate(aurora, startTime, endTime)
		if err != nil {
			log.Fatalf("couldn't get %s aggregate data for window %s - %s: %v",
				tableFlag, startTime.Format(time.RFC3339), endTime.Format(time.RFC3339), err)
		}
		if len(storageAggregate) == 0 {
			log.Printf("no %s aggregate storage data for window %s - %s", tableFlag, startTime.Format(time.RFC3339), endTime.Format(time.RFC3339))
		} else {
			log.Printf("processing %d %s storage rows for window %s - %s", len(storageAggregate), tableFlag, startTime.Format(time.RFC3339), endTime.Format(time.RFC3339))

			_, err = retryInsertIntoStorageAggregate(aurora.DB, storageTable, storageAggregate, batchID, maxRetries)
			if err != nil {
				log.Fatalf("couldn't insert into aurora %s table: %v", tableFlag, err)
			}
			if storageTable == metering.MeteringTableStorageHourly {
				// insert into supabase table
				_, err = retryInsertIntoStorageAggregate(supabaseDB, storageTable, storageAggregate, batchID, maxRetries)
				if err != nil {
					log.Fatalf("couldn't insert into supabase %s table: %v", tableFlag, err)
				}
			}
		}
	}
}

func retryInsertIntoStorageAggregate(
	db *sql.DB, table metering.MeteringTable, aggregate []metering.StorageAggregateRow, batch_id string, maxRetries int) (int64, error) {
	var retryErr error
	var rows int64
	retryErr = util.Retry(maxRetries, 2*time.Second, func() error {
		tx, err := db.Begin()
		if err != nil {
			log.Printf("couldn't begin transaction: %v", err)
			return err
		}
		rows, err = metering.InsertRowsIntoStorageAggregate(tx, table, aggregate, batch_id)
		if err != nil {
			rollbackErr := tx.Rollback()
			if rollbackErr != nil {
				return fmt.Errorf("failed to insert rows, rollback txn: %v, %v", err, rollbackErr)
			}
			return fmt.Errorf("failed to execute query, %v", err)
		}
		err = tx.Commit()
		if err != nil {
			rollbackErr := tx.Rollback()
			if rollbackErr != nil {
				return fmt.Errorf("failed to commit txn, rollback txn: %v, %v", err, rollbackErr)
			}
			return fmt.Errorf("failed to commit transaction: %v", err)
		}
		return nil
	})
	if retryErr != nil {
		return 0, retryErr
	}
	return rows, nil
}

func retryInsertIntoComputeAggregate(
	db *sql.DB, table metering.MeteringTable, aggregate []metering.ComputeAggregateRow, batch_id string, maxRetries int) (int64, error) {
	var retryErr error
	var rows int64
	retryErr = util.Retry(maxRetries, 2*time.Second, func() error {
		tx, err := db.Begin()
		if err != nil {
			log.Printf("couldn't begin transaction: %v", err)
			return err
		}
		rows, err = metering.InsertRowsIntoComputeAggregate(tx, table, aggregate, batch_id)
		if err != nil {
			rollbackErr := tx.Rollback()
			if rollbackErr != nil {
				return fmt.Errorf("failed to insert rows, rollback txn: %v, %v", err, rollbackErr)
			}
			return fmt.Errorf("failed to execute query, %v", err)
		}
		err = tx.Commit()
		if err != nil {
			rollbackErr := tx.Rollback()
			if rollbackErr != nil {
				return fmt.Errorf("failed to commit txn, rollback txn: %v, %v", err, rollbackErr)
			}
			return fmt.Errorf("failed to commit transaction: %v", err)
		}
		return nil
	})
	if retryErr != nil {
		return 0, retryErr
	}
	return rows, nil
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
