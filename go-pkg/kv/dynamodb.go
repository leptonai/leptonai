package kv

import (
	"fmt"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/awserr"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/dynamodb"
	"github.com/aws/aws-sdk-go/service/dynamodb/dynamodbattribute"
)

var (
	ErrNotExist = fmt.Errorf("key does not exist")
)

type KVDynamoDB struct {
	svc       *dynamodb.DynamoDB
	tableName string
}

type kvDynamoDBItem struct {
	Key   string `json:"key"`
	Value string `json:"value"`
}

func NewKVDynamoDB(name, region string) (*KVDynamoDB, error) {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String(region),
	})
	if err != nil {
		return nil, err
	}

	svc := dynamodb.New(sess)

	_, err = svc.DescribeTable(&dynamodb.DescribeTableInput{
		TableName: aws.String(name),
	})
	if err != nil {
		awsErr, ok := err.(awserr.Error)
		if !ok {
			return nil, err
		}

		if awsErr.Code() == dynamodb.ErrCodeResourceNotFoundException {
			err = createTable(svc, name)
			if err != nil {
				return nil, err
			}
			err = svc.WaitUntilTableExists(&dynamodb.DescribeTableInput{
				TableName: aws.String(name),
			})
			if err != nil {
				return nil, err
			}
		} else {
			return nil, err
		}
	}

	return &KVDynamoDB{
		svc:       svc,
		tableName: name,
	}, nil
}

func (kv *KVDynamoDB) Put(key string, value string) error {
	item := kvDynamoDBItem{
		Key:   key,
		Value: value,
	}

	av, err := dynamodbattribute.MarshalMap(item)
	if err != nil {
		return err
	}

	input := &dynamodb.PutItemInput{
		TableName: aws.String(kv.tableName),
		Item:      av,
	}

	_, err = kv.svc.PutItem(input)
	return err
}

func (kv *KVDynamoDB) Get(key string) (string, error) {
	input := &dynamodb.GetItemInput{
		TableName: aws.String(kv.tableName),
		Key: map[string]*dynamodb.AttributeValue{
			"key": {S: aws.String(key)},
		},
	}

	result, err := kv.svc.GetItem(input)
	if err != nil {
		return "", err
	}
	if result.Item == nil {
		return "", ErrNotExist
	}

	item := kvDynamoDBItem{}

	err = dynamodbattribute.UnmarshalMap(result.Item, &item)
	if err != nil {
		return "", err
	}

	return item.Value, nil
}

func (kv *KVDynamoDB) Delete(key string) error {
	input := &dynamodb.DeleteItemInput{
		TableName: aws.String(kv.tableName),
		Key: map[string]*dynamodb.AttributeValue{
			"key": {S: aws.String(key)},
		},
	}

	_, err := kv.svc.DeleteItem(input)
	return err
}

func (kv *KVDynamoDB) Destroy() error {
	input := &dynamodb.DeleteTableInput{
		TableName: aws.String(kv.tableName),
	}

	_, err := kv.svc.DeleteTable(input)
	return err
}

func createTable(svc *dynamodb.DynamoDB, tableName string) error {
	input := &dynamodb.CreateTableInput{
		AttributeDefinitions: []*dynamodb.AttributeDefinition{
			{
				AttributeName: aws.String("key"),
				AttributeType: aws.String("S"),
			},
		},
		KeySchema: []*dynamodb.KeySchemaElement{
			{
				AttributeName: aws.String("key"),
				KeyType:       aws.String("HASH"),
			},
		},
		ProvisionedThroughput: &dynamodb.ProvisionedThroughput{
			ReadCapacityUnits:  aws.Int64(500),
			WriteCapacityUnits: aws.Int64(5),
		},
		TableName: aws.String(tableName),
	}

	_, err := svc.CreateTable(input)
	return err
}
