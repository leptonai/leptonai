package main

import (
	"fmt"
	"log"
	"net"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/awserr"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/route53"
)

func timer(name string) func() {
	start := time.Now()
	return func() {
		fmt.Printf("%s took %v\n", name, time.Since(start))
	}
}

func listDNSRecords(r53 *route53.Route53) {
	input := &route53.GetHostedZoneInput{
		Id: aws.String("Z007822916VK7B4DFVMP7"),
	}

	result, err := r53.GetHostedZone(input)
	if err != nil {
		if aerr, ok := err.(awserr.Error); ok {
			switch aerr.Code() {
			case route53.ErrCodeNoSuchHostedZone:
				fmt.Println(route53.ErrCodeNoSuchHostedZone, aerr.Error())
			case route53.ErrCodeInvalidInput:
				fmt.Println(route53.ErrCodeInvalidInput, aerr.Error())
			default:
				fmt.Println(aerr.Error())
			}
		} else {
			// Print the error, cast err to awserr.Error to get the Code and
			// Message from an error.
			fmt.Println(err.Error())
		}
		return
	}
	fmt.Println(result)
}

func addDNSRecord(r53 *route53.Route53, name string) string {
	defer timer("addDNSRecord")()
	input := &route53.ChangeResourceRecordSetsInput{
		ChangeBatch: &route53.ChangeBatch{
			Changes: []*route53.Change{
				{
					Action: aws.String("CREATE"),
					ResourceRecordSet: &route53.ResourceRecordSet{
						Name: aws.String(name),
						ResourceRecords: []*route53.ResourceRecord{
							{
								Value: aws.String("8.8.8.8"),
							},
						},
						TTL:  aws.Int64(60),
						Type: aws.String("A"),
					},
				},
			},
			Comment: aws.String("Example to test DNS propagation time"),
		},
		HostedZoneId: aws.String("Z007822916VK7B4DFVMP7"),
	}
	output, err := r53.ChangeResourceRecordSets(input)
	log.Printf("output: %v", output)
	if err != nil {
		log.Printf("failed to add dns record - %s\n", err)
	}
	return *output.ChangeInfo.Id
}

func loopLookUpIP(r53 *route53.Route53, url string, requestId string) {
	defer timer("loopLookUpIP")()
	for {
		getChange(r53, requestId)
		ips, err := net.LookupIP(url)
		if err != nil {
			log.Printf("could not get IPs: %v\n", err)
		}
		for _, ip := range ips {
			log.Printf("%v. IN A %s\n", url, ip.String())
			return
		}
		time.Sleep(5 * time.Second)
	}
}

func getChange(r53 *route53.Route53, id string) {
	input := &route53.GetChangeInput{
		Id: &id,
	}

	output, err := r53.GetChange(input)
	if err != nil {
		log.Printf("failed to query change - %s\n", err)
	}
	log.Printf("output: %v", output)
}

func main() {
	sess, err := session.NewSessionWithOptions(session.Options{
		// Specify profile to load for the session's config
		Profile: "default",

		// Force enable Shared Config support
		SharedConfigState: session.SharedConfigEnable,
	})
	if err != nil {
		fmt.Println(err.Error())
	}
	r53 := route53.New(sess)
	name := "testdns0008.cloud.lepton.ai"

	listDNSRecords(r53)
	requestId := addDNSRecord(r53, name)
	listDNSRecords(r53)
	loopLookUpIP(r53, name, requestId)
}

// #!/bin/bash
// NAMESERVERS=("ns-2014.awsdns-59.co.uk" "ns-1432.awsdns-51.org" "ns-585.awsdns-09.net" "ns-42.awsdns-05.com")

// for ns in "${NAMESERVERS[@]}"
// do
//   echo "nameserver: $ns"
//   nslookup $1 $ns
// done
