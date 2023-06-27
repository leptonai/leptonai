package httpapi

import (
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/http/httptest"
	"net/http/httputil"
	"net/url"
	"strconv"
	"sync"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/kv"

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

	for key, values := range response.Header {
		for _, value := range values {
			c.Writer.Header().Add(key, value)
		}
	}
	c.Writer.Header().Del("Content-Length")
	c.Writer.Header().Del("Content-Encoding")

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
		log.Println("failed to add job id in DB:", err)
		c.Status(http.StatusInternalServerError)
		return
	}

	c.JSON(response.StatusCode, j)
}

func (jh *JobHandler) GetJobByID(c *gin.Context) {
	jh.checkIDAndForward(c)
}

func (jh *JobHandler) CancelJob(c *gin.Context) {
	id := jh.checkIDAndForward(c)

	err := jh.kv.Delete(id)
	if err != nil {
		log.Println("failed to delete job id in DB:", err)
	}
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
		log.Println("failed to get job id in DB:", err)
		if err == kv.ErrNotExist {
			c.Status(http.StatusNotFound)
		} else {
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

	for key, values := range response.Header {
		for _, value := range values {
			c.Writer.Header().Add(key, value)
		}
	}
	c.Writer.Header().Del("Content-Length")
	c.Writer.Header().Del("Content-Encoding")

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
				log.Println("failed to get job id in DB:", err)
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
	c.Request.URL.Host = "tuna-prod.vercel.app"
	c.Request.Host = "tuna-prod.vercel.app"
}
