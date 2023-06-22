package kv

import (
	"testing"

	"github.com/leptonai/lepton/go-pkg/util"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/awserr"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/dynamodb"
)

func TestDynamoDB(t *testing.T) {
	tname := "test-kv-" + util.RandString(6)
	region := "us-east-1"
	kv, err := NewKVDynamoDB(tname, region)
	if err != nil {
		t.Fatal("Failed to create KVDynamoDB instance:", err)
	}
	defer func() {
		err := kv.Destroy()
		if err != nil {
			t.Fatal("Failed to destroy KVDynamoDB instance:", err)
		}
		mustCheckDynamoDBTableNotExist(t, tname)
	}()

	err = kv.Put("key1", "value1")
	if err != nil {
		t.Fatal("Failed to put item:", err)
	}

	value, err := kv.Get("key1")
	if err != nil {
		t.Fatal("Failed to get item:", err)
	}
	t.Log("Retrieved value:", value)

	err = kv.Delete("key1")
	if err != nil {
		t.Fatal("Failed to delete item:", err)
	}

	value, err = kv.Get("key1")
	if err == nil {
		t.Fatal("Failed to delete item:", value)
	}
}

func mustCheckDynamoDBTableNotExist(t *testing.T, name string) {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"), // Set your preferred AWS region
	})
	if err != nil {
		t.Fatal("Failed to create AWS session:", err)
	}
	svc := dynamodb.New(sess)

	input := &dynamodb.DescribeTableInput{
		TableName: aws.String(name),
	}
	s, err := svc.DescribeTable(input)
	if awsErr, ok := err.(awserr.Error); ok {
		if awsErr.Code() == dynamodb.ErrCodeResourceNotFoundException {
			return
		}
	}
	if *s.Table.TableStatus != dynamodb.TableStatusDeleting {
		t.Fatal("Table status ", *s.Table.TableStatus)
	}
}
