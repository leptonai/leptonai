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

	"github.com/gin-gonic/gin"
)

// Job represents a job entity
type Job struct {
	ID         int    `json:"id"`
	CreatedAt  string `json:"created_at"`
	ModifiedAt string `json:"modified_at"`
	Status     string `json:"status"`
}

type JobHandler struct {
	proxy *httputil.ReverseProxy
	// TODO: persist me in DB
	isMyJob map[int]bool
}

func NewJobHandler(url *url.URL) *JobHandler {
	proxy := httputil.NewSingleHostReverseProxy(url)
	return &JobHandler{
		proxy:   proxy,
		isMyJob: make(map[int]bool),
	}
}

func (jh *JobHandler) AddJob(c *gin.Context) {
	r := httptest.NewRecorder()

	setForwardURL(c)
	jh.proxy.ServeHTTP(r, c.Request)
	response := r.Result()

	for key, values := range response.Header {
		for _, value := range values {
			c.Writer.Header().Add(key, value)
		}
	}

	c.Writer.WriteHeader(response.StatusCode)
	if response.StatusCode >= 300 {
		io.Copy(c.Writer, response.Body)
		return
	}

	var j Job
	err := json.NewDecoder(response.Body).Decode(&j)
	if err != nil {
		panic(err)
	}
	jh.isMyJob[j.ID] = true

	err = json.NewEncoder(c.Writer).Encode(j)
	if err != nil {
		log.Println(err)
	}
}

func (jh *JobHandler) GetJobByID(c *gin.Context) {
	jh.checkIDAndForward(c)
}

func (jh *JobHandler) CancelJob(c *gin.Context) {
	id := jh.checkIDAndForward(c)
	// todo: check return code. only delete if 200
	delete(jh.isMyJob, id)
}

func (jh *JobHandler) ListJobs(c *gin.Context) {
	jh.filterByMyJob(c)
}

func (jh *JobHandler) ListJobsByStatus(c *gin.Context) {
	jh.filterByMyJob(c)
}

func (jh *JobHandler) checkIDAndForward(c *gin.Context) int {
	jobID, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		c.Status(http.StatusBadRequest)
	}

	if !jh.isMyJob[jobID] {
		c.Status(http.StatusNotFound)
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

	c.Writer.WriteHeader(response.StatusCode)

	if response.StatusCode >= 300 {
		io.Copy(c.Writer, response.Body)
		return
	}

	var js []Job
	err := json.NewDecoder(response.Body).Decode(&js)
	if err != nil {
		panic(err)
	}

	var myJobs []Job
	for _, j := range js {
		if jh.isMyJob[j.ID] {
			myJobs = append(myJobs, j)
		}
	}

	err = json.NewEncoder(c.Writer).Encode(myJobs)
	if err != nil {
		log.Println(err)
	}
}

func setForwardURL(c *gin.Context) {
	c.Request.URL.Path = c.Request.URL.Path[len("/api/v1/tuna"):]
	c.Request.URL.Scheme = "https"
	c.Request.URL.Host = "tuna-tunaml.vercel.app"
	c.Request.Host = "tuna-tunaml.vercel.app"
}
