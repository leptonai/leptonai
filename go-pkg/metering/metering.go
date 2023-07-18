// package metering implements type definitions and functions for opencost usage metering
package metering

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/leptonai/lepton/go-pkg/k8s/service"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	"github.com/opencost/opencost/pkg/kubecost"
	"k8s.io/client-go/kubernetes"
)

type AuroraDB struct {
	DB *sql.DB
}

type SupabaseDB struct {
	DB *sql.DB
}

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

type MeteringTable string

const (
	MeteringTableFineGrain      MeteringTable = "fine_grain"
	MeteringTableAuroraHourly   MeteringTable = "hourly_metering"
	MeteringTableSupabaseHourly MeteringTable = "hourly_metering"
	MeteringTableHourly         MeteringTable = "hourly_metering"
	MeteringTableDaily          MeteringTable = "daily_metering"
	MeteringTableWeekly         MeteringTable = "weekly_metering"
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

type FineGrainData struct {
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

// GetFineGrainData queries kubecost service forwarded by fwd, for raw allocation data given query parameters qp
func GetFineGrainData(clientset *kubernetes.Clientset, fwd *service.PortForwardQuerier, qp OcQueryParams) ([]FineGrainData, error) {
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

	data := make([]FineGrainData, 0, len(ar.Data))
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
			d := FineGrainData{
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

func BatchInsertIntoFineGrain(tx *sql.Tx, rows []FineGrainData) (int64, error) {
	FineGrainInsert := fmt.Sprintf(`INSERT INTO %s (
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
	VALUES `, MeteringTableFineGrain)

	// Generate a batch query ID
	id, err := uuid.NewRandom()
	if err != nil {
		return 0, err
	}
	rowStr := genRowStr(9)
	var toInsert []string
	var vals []interface{}
	for _, r := range rows {
		toInsert = append(toInsert, rowStr)
		vals = append(vals, id, r.Namespace, r.LeptonDeploymentName, r.PodName, r.PodShape, time.Unix(r.Start, 0), time.Unix(r.End, 0), r.Window, r.RunningMinutes)
	}
	sqlStr := FineGrainInsert + strings.Join(toInsert, ",")
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
	if affected != int64(len(rows)) {
		return 0, fmt.Errorf("expected %d rows affected, got %d", len(rows), affected)
	}

	return affected, nil
}

func SyncToDB(aurora AuroraDB, data []FineGrainData) error {
	db := aurora.DB
	// todo: check if tables exist
	tx, err := db.Begin()
	if err != nil {
		return err
	}
	defer func() {
		err = fmt.Errorf("%v \n %s", err, tx.Rollback())
	}()
	// Insert into fine_grain
	if len(data) > 0 {
		affected, err := BatchInsertIntoFineGrain(tx, data)
		if err != nil {
			return err
		}
		goutil.Logger.Infof("Inserted %d rows into %s", affected, MeteringTableFineGrain)
	}
	return tx.Commit()
}

// returns the most recent query's start and end time, or zero time if table is empty
func GetMostRecentFineGrainEntry(aurora AuroraDB) (time.Time, time.Time, error) {
	db := aurora.DB
	// check if table is empty
	var count int
	err := db.QueryRow(fmt.Sprintf("SELECT count(*) FROM (SELECT 1 FROM %s LIMIT 1) AS t", MeteringTableFineGrain)).Scan(&count)
	if err != nil {
		return time.Time{}, time.Time{}, err
	}
	if count == 0 {
		return time.Time{}, time.Time{}, nil
	}

	var start, end time.Time
	err = db.QueryRow(
		fmt.Sprintf("SELECT query_start, query_end FROM %s ORDER BY query_end DESC LIMIT 1", MeteringTableFineGrain)).Scan(&start, &end)
	if err != nil {
		return time.Time{}, time.Time{}, err
	}
	return start, end, nil
}
