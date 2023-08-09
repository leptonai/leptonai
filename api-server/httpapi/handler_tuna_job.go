package httpapi

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"net/http/httputil"
	"net/url"
	"strconv"
	"sync"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/kv"
	goutil "github.com/leptonai/lepton/go-pkg/util"

	"github.com/gin-gonic/gin"
)

// Job represents a job entity
type Job struct {
	ID         int    `json:"id"`
	Name       string `json:"name"`
	CreatedAt  string `json:"created_at"`
	ModifiedAt string `json:"modified_at"`
	Status     string `json:"status"`
	OutputDir  string `json:"output_dir"`
}

type JobHandler struct {
	proxy *httputil.ReverseProxy
	// TODO: persist me in DB
	kv *kv.KVDynamoDB
}

func NewJobHandler(url *url.URL, kv *kv.KVDynamoDB) *JobHandler {
	proxy := httputil.NewSingleHostReverseProxy(url)
	return &JobHandler{
		proxy: proxy,
		kv:    kv,
	}
}

func (jh *JobHandler) AddJob(c *gin.Context) {
	r := httptest.NewRecorder()
	name := c.DefaultQuery("name", "")

	setForwardURL(c)
	jh.proxy.ServeHTTP(r, c.Request)
	response := r.Result()

	copyResponseHeader(c, response.Header)

	if response.StatusCode >= 300 {
		c.Writer.WriteHeader(response.StatusCode)
		io.Copy(c.Writer, response.Body)
		return
	}

	var j Job
	err := json.NewDecoder(response.Body).Decode(&j)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}

	err = jh.kv.Put(strconv.Itoa(j.ID), name)
	if err != nil {
		goutil.Logger.Errorw("failed to create job in DB",
			"operation", "AddJob",
			"job", j.ID,
			"error", err,
		)
		c.Status(http.StatusInternalServerError)
		return
	}

	goutil.Logger.Infow("created job",
		"operation", "AddJob",
		"job", j.ID,
	)
	c.JSON(response.StatusCode, j)
}

func (jh *JobHandler) GetJobByID(c *gin.Context) {
	jh.checkIDAndForward(c)
}

func (jh *JobHandler) CancelJob(c *gin.Context) {
	id := jh.checkIDAndForward(c)

	err := jh.kv.Delete(id)
	if err != nil {
		goutil.Logger.Errorw("failed to delete job in DB",
			"operation", "CancelJob",
			"job", id,
			"error", err,
		)
		c.Status(http.StatusInternalServerError)
		return
	}

	goutil.Logger.Infow("canceled job",
		"operation", "CancelJob",
		"job", id,
	)
	c.Status(http.StatusOK)
}

func (jh *JobHandler) ListJobs(c *gin.Context) {
	jh.filterByMyJob(c)
}

func (jh *JobHandler) ListJobsByStatus(c *gin.Context) {
	jh.filterByMyJob(c)
}

func (jh *JobHandler) checkIDAndForward(c *gin.Context) string {
	jobID := (c.Param("id"))
	_, err := jh.kv.Get(jobID)
	if err != nil {
		if err == kv.ErrNotExist {
			c.Status(http.StatusNotFound)
		} else {
			goutil.Logger.Errorw("failed to get job id in DB",
				"operation", "checkIDAndForward",
				"job", jobID,
				"error", err,
			)
			c.Status(http.StatusInternalServerError)
		}
		return jobID
	}

	setForwardURL(c)
	jh.proxy.ServeHTTP(c.Writer, c.Request)

	return jobID
}

func (jh *JobHandler) filterByMyJob(c *gin.Context) {
	r := httptest.NewRecorder()

	setForwardURL(c)
	jh.proxy.ServeHTTP(r, c.Request)
	response := r.Result()

	copyResponseHeader(c, response.Header)

	if response.StatusCode >= 300 {
		c.Writer.WriteHeader(response.StatusCode)
		io.Copy(c.Writer, response.Body)
		return
	}

	var js []Job
	err := json.NewDecoder(response.Body).Decode(&js)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}

	var (
		mu sync.Mutex
		wg sync.WaitGroup
	)
	myJobs := []Job{}
	for _, j := range js {
		// todo: use batch get
		wg.Add(1)
		go func(j Job) {
			name, err := jh.kv.Get(strconv.Itoa(j.ID))
			if err == nil {
				j.Name = name
				mu.Lock()
				myJobs = append(myJobs, j)
				mu.Unlock()
			}
			if err != nil && err != kv.ErrNotExist {
				goutil.Logger.Errorw("failed to get job id in DB",
					"operation", "filterByMyJob",
					"job", j.ID,
					"error", err,
				)
			}
			wg.Done()
		}(j)
	}
	wg.Wait()

	c.JSON(http.StatusOK, myJobs)
}

func setForwardURL(c *gin.Context) {
	values := c.Request.URL.Query()
	if values.Has("name") {
		values.Del("name")
		c.Request.URL.RawQuery = values.Encode()
	}
	c.Request.Header.Del("Authorization")
	c.Request.Header.Del("Accept-Encoding")
	c.Request.URL.Path = c.Request.URL.Path[len("/api/v1/tuna"):]
	c.Request.URL.Scheme = "https"
	c.Request.URL.Host = "tuna-dev.vercel.app"
	c.Request.Host = "tuna-dev.vercel.app"
}

var removingResponseHeaders = map[string]bool{
	"Content-Length":                   true,
	"Content-Encoding":                 true,
	"Access-Control-Allow-Origin":      true,
	"Access-Control-Allow-Credentials": true,
	"Access-Control-Allow-Headers":     true,
	"Access-Control-Allow-Methods":     true,
}

func copyResponseHeader(c *gin.Context, header http.Header) {
	for key, values := range header {
		if removingResponseHeaders[key] {
			continue
		}
		for _, value := range values {
			c.Writer.Header().Add(key, value)
		}
	}
}