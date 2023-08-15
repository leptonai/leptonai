package metering

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
	efs "github.com/leptonai/lepton/go-pkg/aws/efs"
)

const VolumePrefix = "efs-lepton-"

type FineGrainStorageData struct {
	Cluster     string
	Workspace   string
	storageID   string
	SizeInBytes uint64
	Size        string
	Time        time.Time
}

func GetFineGrainStorageData(queryTime time.Time, region string, clusterName string) ([]FineGrainStorageData, error) {
	cfg, err := aws.New(&aws.Config{
		DebugAPICalls: false,
		Region:        region,
	})
	if err != nil {
		return nil, err
	}

	filter := map[string]string{"LeptonClusterName": clusterName}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	fss, err := efs.ListFileSystems(ctx, cfg, filter)
	cancel()
	if err != nil {
		return nil, err
	}
	var data []FineGrainStorageData
	for _, fs := range fss {
		data = append(data, FineGrainStorageData{
			Cluster:     clusterName,
			Workspace:   strings.ReplaceAll(fs.Name, VolumePrefix, ""),
			storageID:   fs.ID,
			SizeInBytes: fs.SizeInUseBytes,
			Size:        fs.SizeInUse,
			Time:        queryTime,
		})
	}
	return data, nil
}

func BatchInsertIntoFineGrainStorage(tx *sql.Tx, data []FineGrainStorageData, batchID string) (int64, error) {
	cmd := fmt.Sprintf(`INSERT INTO %s (
		query_id,
		cluster,
		workspace,
		storage_id,
		size_bytes,
		size_text,
		time
	)
	VALUES `, MeteringTableStorageFineGrain)
	rowStr := genRowStr(7)
	var toInsert []string
	var vals []interface{}
	batchSize := 0
	affected := int64(0)
	for _, d := range data {
		toInsert = append(toInsert, rowStr)
		vals = append(vals, batchID, d.Cluster, d.Workspace, d.storageID, d.SizeInBytes, d.Size, d.Time)
		batchSize++
		if batchSize >= insertBatchSize {
			res, err := sqlInsert(tx, cmd, toInsert, "", vals)
			if err != nil {
				return 0, err
			}
			batchAffected, err := res.RowsAffected()
			if err != nil {
				return 0, err
			}
			affected += batchAffected
			batchSize = 0
			toInsert = []string{}
			vals = []interface{}{}
		}
	}
	if batchSize > 0 {
		res, err := sqlInsert(tx, cmd, toInsert, "", vals)
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
