package metering

import (
	"bytes"
	"crypto/md5"
	"database/sql"
	"fmt"
	"sort"
	"strconv"
	"strings"

	"github.com/olekukonko/tablewriter"
)

type AuroraDB struct {
	DB *sql.DB
}

type SupabaseDB struct {
	DB *sql.DB
}

type MeteringTable string

const (
	MeteringTableComputeFineGrain MeteringTable = "compute_fine_grain"
	MeteringTableComputeHourly    MeteringTable = "compute_hourly"
	MeteringTableComputeDaily     MeteringTable = "compute_daily"
	MeteringTableComputeWeekly    MeteringTable = "compute_weekly"

	MeteringTableStorageFineGrain MeteringTable = "storage_fine_grain"
	MeteringTableStorageHourly    MeteringTable = "storage_hourly"
	MeteringTableStorageDaily     MeteringTable = "storage_daily"
	MeteringTableStorageWeekly    MeteringTable = "storage_weekly"

	insertBatchSize = 999
)

func (d FineGrainComputeData) ToTableRow() []string {
	return []string{
		d.Cluster,
		d.Namespace,
		d.LeptonDeploymentName,
		d.PodName,
		d.PodShape,

		fmt.Sprintf("%d", d.Start),
		fmt.Sprintf("%d", d.End),
		fmt.Sprintf("%.5f", d.RunningMinutes),
		d.Window,
	}
}

func PrettyPrint(data []FineGrainComputeData) {
	sort.SliceStable(data, func(i, j int) bool {
		if data[i].Namespace == data[j].Namespace {
			return data[i].PodName < data[j].PodName
		}
		return data[i].Namespace < data[j].Namespace
	})
	rows := make([][]string, 0, len(data))
	for _, d := range data {
		rows = append(rows, d.ToTableRow())
	}

	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetHeader(TableColumns)
	tb.AppendBulk(rows)
	tb.Render()
	fmt.Println(buf.String())
}

// returns comma separated string of namespaces to exclude
// ref: https://docs.kubecost.com/apis/apis-overview/filters-api
func CreateExludeFilterStringForNamespaces(namespaceMap map[string]bool) string {
	var namespaces []string
	for ns := range namespaceMap {
		namespaces = append(namespaces, "\""+ns+"\"")
	}
	return "namespace!:" + strings.Join(namespaces, ",")
}

// generates a string of (?, ?, ?) with given row length, used for prepared SQL inserts
func genRowStr(rowLen int) string {
	var valueStr string
	valueStr += "("
	for i := 0; i < rowLen; i++ {
		valueStr += "?"
		if i != rowLen-1 {
			valueStr += ","
		}
	}
	valueStr += ")"
	return valueStr
}

// replaces the instance occurrence of any string pattern with an increasing $n based sequence
func replaceSQL(old, pattern string) string {
	tmpCount := strings.Count(old, pattern)
	for m := 1; m <= tmpCount; m++ {
		old = strings.Replace(old, pattern, "$"+strconv.Itoa(m), 1)
	}
	return old
}

// performs a batch insert given a transaction, command, and values to insert
func sqlInsert(tx *sql.Tx, cmd string, toInsert []string, onConflict string, vals []interface{}) (sql.Result, error) {
	sqlStr := cmd + strings.Join(toInsert, ",") + onConflict
	sqlStr = replaceSQL(sqlStr, "?")
	stmt, err := tx.Prepare(sqlStr)
	if err != nil {
		return nil, err
	}
	defer stmt.Close()
	return stmt.Exec(vals...)
}

// Get the md5 hash of input strings
func Md5Hex(s ...string) string {
	hash := md5.New()
	for _, str := range s {
		hash.Write([]byte(str))
	}
	hashSum := hash.Sum(nil)
	return fmt.Sprintf("%x", hashSum)
}
