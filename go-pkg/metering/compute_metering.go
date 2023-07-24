// package metering implements type definitions and functions for opencost usage metering
package metering

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/leptonai/lepton/go-pkg/k8s/service"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	"github.com/opencost/opencost/pkg/kubecost"
	"k8s.io/client-go/kubernetes"
)

var (
	// set of namespaces to exclude from the query
	ExcludedNamespaces = map[string]bool{
		"calico-apiserver": true,
		"calico-system":    true,
		"external-dns":     true,
		"gpu-operator":     true,
		"grafana":          true,
		"kube-system":      true,
		"kubecost":         true,
		"prometheus":       true,
		"tigera-operator":  true,
	}

	// columns to be displayed in the table
	TableColumns = []string{
		"cluster",
		"namespace",
		"deployment name",
		"pod name",
		"shape",

		"start",
		"end",
		"running minutes",
		"window",
	}
)

type AllocationResponse struct {
	Code int                              `json:"code"`
	Data []map[string]kubecost.Allocation `json:"data"`
}

type OcQueryParams struct {
	ClusterARN      string
	QueryPath       string
	QueryAgg        string
	QueryResolution string
	QueryAcc        bool
	QueryStart      time.Time
	QueryEnd        time.Time
	QueryWindow     string

	QueryRounds        uint
	QueryInterval      time.Duration
	ExcludedNamespaces map[string]bool
}

type FineGrainComputeData struct {
	Cluster              string
	Namespace            string
	LeptonDeploymentName string
	PodName              string
	PodShape             string

	Start          int64
	End            int64
	Window         string
	RunningMinutes float64
}

// GetFineGrainComputeData queries kubecost service forwarded by fwd, for raw allocation data given query parameters qp
func GetFineGrainComputeData(clientset *kubernetes.Clientset, fwd *service.PortForwardQuerier, qp OcQueryParams) ([]FineGrainComputeData, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	if qp.QueryWindow == "" {
		qp.QueryWindow = fmt.Sprintf("%d", qp.QueryStart.Unix()) + "," + fmt.Sprintf("%d", qp.QueryEnd.Unix())
	}

	filterString := CreateExludeFilterStringForNamespaces(qp.ExcludedNamespaces)
	queryRs, err := fwd.QueryGet(
		ctx,
		qp.QueryPath,
		map[string]string{
			"window":     qp.QueryWindow,
			"aggregate":  qp.QueryAgg,
			"accumulate": fmt.Sprintf("%v", qp.QueryAcc),
			"resolution": qp.QueryResolution,
			// TODO: filter query string currently doesn't do anything, debug this.
			// Will improve performance if we can filter out excluded namespaces in the API call
			"filter": filterString,
		},
	)
	cancel()
	if err != nil {
		return nil, fmt.Errorf("failed to proxy get kubecost %v", err)
	}

	var ar AllocationResponse
	if err = json.Unmarshal(queryRs, &ar); err != nil {
		return nil, fmt.Errorf("failed to parse allocation response %v", err)
	}

	data := make([]FineGrainComputeData, 0, len(ar.Data))
	for _, a := range ar.Data {
		for _, v := range a {
			// v.Name is same as key in the map
			// v.Name is [cluster name]/[namespace]/[pod id]
			// v.Properties.ProviderID is the instance ID in AWS
			// v.Properties.Cluster is hard-coded as "cluster-one", do not use this
			// ignore excluded namespaces
			if ExcludedNamespaces[v.Properties.Namespace] {
				continue
			}
			// can't use v.Start or v.End:
			// if a pod is not deployed for entire window, v.Start/End will differ from window start/end
			// if qp start, end are set (defaults to unix zero time), use them instead
			actualQueryStart := v.Start
			actualQueryEnd := v.End
			if !qp.QueryStart.IsZero() {
				actualQueryStart = qp.QueryStart
			}
			if !qp.QueryEnd.IsZero() {
				actualQueryEnd = qp.QueryEnd
			}
			d := FineGrainComputeData{
				Cluster:              qp.ClusterARN,
				Namespace:            v.Properties.Namespace,
				LeptonDeploymentName: v.Properties.Labels["lepton_deployment_id"],
				PodName:              v.Properties.Pod,
				PodShape:             v.Properties.Labels["lepton_deployment_shape"],

				Start:          actualQueryStart.Unix(),
				End:            actualQueryEnd.Unix(),
				RunningMinutes: v.Minutes(),
				Window:         v.Window.Duration().String(),
			}
			data = append(data, d)
		}
	}
	return data, nil
}

func BatchInsertIntoFineGrain(tx *sql.Tx, data []FineGrainComputeData, batchID string) (int64, error) {
	cmd := fmt.Sprintf(`INSERT INTO %s (
		query_id,
		namespace,
		deployment_name,
		pod_name,
		shape,
		query_start,
		query_end,
		query_window,
		minutes
	)
	VALUES `, MeteringTableComputeFineGrain)

	rowStr := genRowStr(9)
	var toInsert []string
	var vals []interface{}
	affected := int64(0)
	for _, d := range data {
		toInsert = append(toInsert, rowStr)
		vals = append(vals, batchID, d.Namespace, d.LeptonDeploymentName, d.PodName, d.PodShape, time.Unix(d.Start, 0), time.Unix(d.End, 0), d.Window, d.RunningMinutes)
		if len(toInsert) >= insertBatchSize {
			res, err := sqlInsert(tx, cmd, toInsert, "", vals)
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

// SyncToFineGrain handles the transaction for inserting fine grain compute and storage data into Aurora
func SyncToFineGrain(aurora AuroraDB, computeData []FineGrainComputeData, storageData []FineGrainStorageData) error {
	db := aurora.DB
	// todo: check if tables exist
	tx, err := db.Begin()
	if err != nil {
		return err
	}
	defer func() {
		err = fmt.Errorf("%v \n %s", err, tx.Rollback())
	}()
	// Generate a batch query ID
	batchID, _ := uuid.NewRandom()
	batchIDStr := batchID.String()
	// Insert into fine_grain
	if len(computeData) > 0 {
		affected, err := BatchInsertIntoFineGrain(tx, computeData, batchIDStr)
		if err != nil {
			return err
		}
		goutil.Logger.Infof("Inserted %d rows into %s", affected, MeteringTableComputeFineGrain)
	}
	if len(storageData) > 0 {
		affected, err := BatchInsertIntoFineGrainStorage(tx, storageData, batchIDStr)
		if err != nil {
			return err
		}
		goutil.Logger.Infof("Inserted %d rows into %s", affected, MeteringTableStorageFineGrain)
	}
	return tx.Commit()
}

// returns the most recent query's start and end time, or zero time if table is empty
// case compute fine grain: return query start, end of most recent window
// case compute storage fine grain: returns one time only, since storage is measured at discrete points.
func GetMostRecentFineGrainEntry(aurora AuroraDB, table MeteringTable) (time.Time, time.Time, error) {
	db := aurora.DB
	if (table != MeteringTableComputeFineGrain) && (table != MeteringTableStorageFineGrain) {
		return time.Time{}, time.Time{}, fmt.Errorf("invalid table %s", table)
	}
	// check if table is empty
	var count int
	err := db.QueryRow(fmt.Sprintf("SELECT count(*) FROM (SELECT 1 FROM %s LIMIT 1) AS t", table)).Scan(&count)
	if err != nil {
		return time.Time{}, time.Time{}, err
	}
	if count == 0 {
		return time.Time{}, time.Time{}, nil
	}

	var start, end time.Time
	switch table {
	case MeteringTableComputeFineGrain:
		err = db.QueryRow(
			fmt.Sprintf("SELECT query_start, query_end FROM %s ORDER BY query_end DESC LIMIT 1", table)).Scan(&start, &end)
		if err != nil {
			return time.Time{}, time.Time{}, err
		}
		return start, end, nil
	case MeteringTableStorageFineGrain:
		err = db.QueryRow(
			fmt.Sprintf("SELECT time from %s ORDER BY time DESC LIMIT 1", table)).Scan(&end)
		if err != nil {
			return time.Time{}, time.Time{}, err
		}
		return end, end, nil
	default:
		return time.Time{}, time.Time{}, fmt.Errorf("invalid table %s", table)
	}
}
