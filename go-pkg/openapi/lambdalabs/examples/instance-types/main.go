package main

import (
	"context"
	"log"
	"os"
	"time"

	openapiclient "github.com/leptonai/lepton/go-pkg/openapi/lambdalabs"
)

// LAMBDALABS_SECRET=... go run main.go
func main() {
	lls := os.Getenv("LAMBDALABS_SECRET")
	if lls == "" {
		return
	}

	configuration := openapiclient.NewConfiguration()
	configuration.DefaultHeader["Authorization"] = "Bearer " + lls
	apiClient := openapiclient.NewAPIClient(configuration)

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	resp, httpRes, err := apiClient.DefaultAPI.InstanceTypes(ctx).Execute()
	cancel()
	if err != nil {
		log.Fatal(err)
	}

	log.Printf("API response: %+v", *resp)
	log.Printf("HTTP response: %+v", *httpRes)
}
