// package metering implements type definitions and functions for opencost usage metering
package metering

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"time"

	"github.com/leptonai/lepton/go-pkg/k8s/service"
	goutil "github.com/leptonai/lepton/go-pkg/util"

	"github.com/google/uuid"
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
	OCSvcName       string
	OCNamespace     string
	OCPort          int
	ClusterName     string
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

// GetFineGrainComputeDataExternal queries kubecost service forwarded by fwd, for raw allocation data given query parameters qp
func GetFineGrainComputeDataExternal(clientset *kubernetes.Clientset, fwd *service.PortForwardQuerier, qp OcQueryParams) ([]FineGrainComputeData, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	if qp.QueryWindow == "" {
		qp.QueryWindow = fmt.Sprintf("%d", qp.QueryStart.Unix()) + "," + fmt.Sprintf("%d", qp.QueryEnd.Unix())
	}
	filterString := CreateExludeFilterStringForNamespaces(qp.ExcludedNamespaces)
	var queryRs []byte
	var queryErr error
	// if clientset and port forwarder are nil, query on-cluster
	params := map[string]string{
		"window":     qp.QueryWindow,
		"aggregate":  qp.QueryAgg,
		"accumulate": fmt.Sprintf("%v", qp.QueryAcc),
		"resolution": qp.QueryResolution,
		// TODO: filter query string currently doesn't do anything, debug this.
		// Will improve performance if we can filter out excluded namespaces in the API call.
		"filter": filterString,
	}
	queryRs, queryErr = fwd.QueryGet(ctx, qp.QueryPath, params)
	cancel()
	if queryErr != nil {
		return nil, fmt.Errorf("failed to proxy get kubecost %v", queryErr)
	}

	var ar AllocationResponse
	if err := json.Unmarshal(queryRs, &ar); err != nil {
		return nil, fmt.Errorf("failed to parse allocation response %v", err)
	}

	return fineGrainComputeDataFromResponse(ar, qp)
}

func GetFineGrainComputeDataInCluster(qp OcQueryParams) ([]FineGrainComputeData, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	if qp.QueryWindow == "" {
		qp.QueryWindow = fmt.Sprintf("%d", qp.QueryStart.Unix()) + "," + fmt.Sprintf("%d", qp.QueryEnd.Unix())
	}

	filterString := CreateExludeFilterStringForNamespaces(qp.ExcludedNamespaces)
	var queryRs []byte
	var queryErr error
	// if clientset and port forwarder are nil, query on-cluster
	params := map[string]string{
		"window":     qp.QueryWindow,
		"aggregate":  qp.QueryAgg,
		"accumulate": fmt.Sprintf("%v", qp.QueryAcc),
		"resolution": qp.QueryResolution,
		// TODO: filter query string currently doesn't do anything, debug this.
		// Will improve performance if we can filter out excluded namespaces in the API call.
		"filter": filterString,
	}

	queryRs, queryErr = queryKubeCostInCluster(ctx, qp.OCSvcName, qp.OCNamespace, qp.OCPort, qp.QueryPath, params)
	cancel()
	if queryErr != nil {
		return nil, fmt.Errorf("failed to proxy get kubecost %v", queryErr)
	}

	var ar AllocationResponse
	if err := json.Unmarshal(queryRs, &ar); err != nil {
		return nil, fmt.Errorf("failed to parse allocation response %v", err)
	}

	return fineGrainComputeDataFromResponse(ar, qp)
}

// create list of fine grain compute data from allocation response
func fineGrainComputeDataFromResponse(ar AllocationResponse, qp OcQueryParams) ([]FineGrainComputeData, error) {
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

			// TODO: remove deprecated labels
			deploymentNameLabelDepreciated := v.Properties.Labels["lepton_deployment_name"]
			podShapeLabelDepreciated := v.Properties.Labels["lepton_deployment_shape"]

			deploymentNameLabel := v.Properties.Labels["deployment_lepton_ai_name"]
			podShapeLabel := v.Properties.Labels["deployment_lepton_ai_shape"]

			// use deprecated labels if new labels are not set
			if len(deploymentNameLabelDepreciated) > 0 && len(deploymentNameLabel) == 0 {
				deploymentNameLabel = deploymentNameLabelDepreciated
			}
			if len(podShapeLabelDepreciated) > 0 && len(podShapeLabel) == 0 {
				podShapeLabel = podShapeLabelDepreciated
			}

			// if chargeback label is set to v, charge the namespace v instead
			namespace := v.Properties.Namespace
			chargebackLabel := v.Properties.Labels["chargeback_lepton_ai_workspace"]
			if len(chargebackLabel) > 0 {
				namespace = fmt.Sprintf("ws-%s", chargebackLabel)
			}

			d := FineGrainComputeData{
				Cluster:              qp.ClusterName,
				Namespace:            namespace,
				LeptonDeploymentName: deploymentNameLabel,
				PodName:              v.Properties.Pod,
				PodShape:             podShapeLabel,

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

func queryKubeCostInCluster(ctx context.Context, opencostSvcName string, opencostNamespace string, opencostSvcPort int, path string, params map[string]string) ([]byte, error) {
	baseURL := fmt.Sprintf("http://%s.%s.svc.cluster.local:%d", opencostSvcName, opencostNamespace, opencostSvcPort)
	fullPath, err := url.JoinPath(baseURL, "model", path)
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequestWithContext(
		ctx,
		"GET",
		fullPath,
		nil,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create base query request: %s", err)
	}

	q := req.URL.Query()
	for key, val := range params {
		q.Add(key, val)
	}
	req.URL.RawQuery = q.Encode()

	goutil.Logger.Debugf("executing GET to URL %q", req.URL.String())

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to GET %s: %s", fullPath, err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read %s response body: %s", fullPath, err)
	}
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("received non-200 status code %d and data: %s", resp.StatusCode, body)
	}

	return body, nil
}

// SyncToFineGrain handles the transaction for inserting fine grain compute and storage data into Aurora
func SyncToFineGrain(aurora AuroraDB, cluster string, computeData []FineGrainComputeData, storageData []FineGrainStorageData) (err error) {
	db := aurora.DB
	// todo: check if tables exist
	tx, err := db.Begin()
	if err != nil {
		return
	}
	defer func() {
		if err != nil {
			err = fmt.Errorf("%v \n %s", err, tx.Rollback())
			return
		}
		err = tx.Commit()
	}()
	// Generate a batch query ID
	batchID, _ := uuid.NewRandom()
	batchIDStr := batchID.String()
	// Insert into fine_grain
	if len(computeData) > 0 {
		var affected int64
		affected, err = BatchInsertIntoComputeFineGrain(tx, computeData, batchIDStr)
		if err != nil {
			return
		}
		goutil.Logger.Infof("Inserted %d rows into %s", affected, MeteringTableComputeFineGrain)
		GatherFineGrain(cluster, string(MeteringTableComputeFineGrain), float64(affected), float64(countLeptonDeployments(computeData)))
	}
	if len(storageData) > 0 {
		var affected int64
		affected, err = BatchInsertIntoFineGrainStorage(tx, storageData, batchIDStr)
		if err != nil {
			return
		}
		goutil.Logger.Infof("Inserted %d rows into %s", affected, MeteringTableStorageFineGrain)
		GatherFineGrain(cluster, string(MeteringTableStorageFineGrain), float64(affected), 0.0)
	}
	return
}

// insert data into compute_fine_grain table with the same batch ID
func BatchInsertIntoComputeFineGrain(tx *sql.Tx, data []FineGrainComputeData, batchID string) (int64, error) {
	cmd := fmt.Sprintf(`INSERT INTO %s (
		query_id,
		cluster,
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

	rowStr := genRowStr(10)
	var toInsert []string
	var vals []interface{}
	affected := int64(0)
	for _, d := range data {
		toInsert = append(toInsert, rowStr)
		vals = append(vals, batchID, d.Cluster, d.Namespace, d.LeptonDeploymentName, d.PodName, d.PodShape, time.Unix(d.Start, 0), time.Unix(d.End, 0), d.Window, d.RunningMinutes)
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

// returns the most recent query's start and end time, or zero time if no data exists for a cluster
// case compute fine grain: return query start, end of most recent window
// case compute storage fine grain: returns one time only, since storage is measured at discrete points.
func GetMostRecentFineGrainEntry(aurora AuroraDB, table MeteringTable, cluster string) (time.Time, time.Time, error) {
	db := aurora.DB
	if (table != MeteringTableComputeFineGrain) && (table != MeteringTableStorageFineGrain) {
		return time.Time{}, time.Time{}, fmt.Errorf("invalid table %s", table)
	}
	// check if table is empty
	var count int
	err := db.QueryRow(fmt.Sprintf("SELECT count(*) FROM (SELECT 1 FROM %s WHERE cluster='%s' LIMIT 1) AS t", table, cluster)).Scan(&count)
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
			fmt.Sprintf("SELECT query_start, query_end FROM %s WHERE cluster='%s' ORDER BY query_end DESC LIMIT 1", table, cluster)).Scan(&start, &end)
		if err != nil {
			return time.Time{}, time.Time{}, err
		}
		return start, end, nil
	case MeteringTableStorageFineGrain:
		err = db.QueryRow(
			fmt.Sprintf("SELECT time from %s WHERE cluster='%s' ORDER BY time DESC LIMIT 1", table, cluster)).Scan(&end)
		if err != nil {
			return time.Time{}, time.Time{}, err
		}
		return end, end, nil
	default:
		return time.Time{}, time.Time{}, fmt.Errorf("invalid table %s", table)
	}
}

// Returns true if no entries are found within the given time window, for a given cluster
func CheckEmptyWindow(auroraDB AuroraDB, cluster string, start, end time.Time) (bool, error) {
	// check if there are any rows in the table during a given window
	db := auroraDB.DB
	row := db.QueryRow(fmt.Sprintf(`SELECT
		count(*)
		from %s
		where cluster='%s' and 
		query_start >= '%s' and query_end <= '%s'`,
		MeteringTableComputeFineGrain,
		cluster,
		start.Format(time.RFC3339),
		end.Format(time.RFC3339),
	))
	var count int
	err := row.Scan(&count)
	if err != nil {
		return false, err
	}
	return count == 0, nil
}

// get all missing fine_grain data between start and end, for a given cluster
func GetGapsInFineGrain(auroraDB AuroraDB, cluster string, start, end time.Time) ([][]time.Time, error) {
	db := auroraDB.DB
	// if table is empty, return the entire window as a gap
	var count int
	err := db.QueryRow(fmt.Sprintf(`SELECT count(*) from %s where cluster='%s'`, MeteringTableComputeFineGrain, cluster)).Scan(&count)
	if err != nil {
		return nil, err
	}
	if count == 0 {
		return [][]time.Time{{start, end}}, nil
	}

	rows, err := db.Query(fmt.Sprintf(`SELECT DISTINCT
		query_start,
		query_end
		from %s
		where cluster='%s' and 
		query_start >= '%s' and query_end <= '%s'
		order by query_start asc, query_end asc`,
		MeteringTableComputeFineGrain,
		cluster,
		start.Format(time.RFC3339),
		end.Format(time.RFC3339),
	))
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	gaps := make([][]time.Time, 0)
	var prevEnd time.Time
	for rows.Next() {
		var start, end time.Time
		if err := rows.Scan(&start, &end); err != nil {
			return nil, err
		}
		// first row found: set prevEnd to end
		if prevEnd.IsZero() {
			prevEnd = end
			continue
		}
		// if there is a gap between the previous end time and the current start time, add it to the list of gaps
		if start.After(prevEnd) {
			gaps = append(gaps, []time.Time{prevEnd, start})
		}

		// prevEnd = max(prevEnd, end)
		if end.After(prevEnd) {
			prevEnd = end
		}
	}
	var lastSyncEnd time.Time
	retryErr := goutil.Retry(3, 2*time.Second, func() error {
		_, lastSyncEnd, err = GetMostRecentFineGrainEntry(auroraDB, MeteringTableComputeFineGrain, cluster)
		return err
	})
	if retryErr != nil {
		log.Fatalf("Failed to get latest sync time: %v", err)
	}
	// if there is a gap between the last sync time and the current time, add it to the list of gaps
	if !lastSyncEnd.IsZero() && lastSyncEnd.Before(end) {
		gaps = append(gaps, []time.Time{lastSyncEnd, end})
	}
	return gaps, nil
}

func countLeptonDeployments(data []FineGrainComputeData) int {
	ld := 0
	for _, d := range data {
		if len(d.LeptonDeploymentName) > 0 && len(d.PodShape) > 0 && d.RunningMinutes > 0 {
			ld++
		}
	}
	return ld
}
