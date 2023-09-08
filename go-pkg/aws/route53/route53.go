package route53

import (
	"context"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/route53"
	"github.com/aws/aws-sdk-go-v2/service/route53/types"
)

// ListRecords lists all records in a hosted zone.
func ListRecords(ctx context.Context, cfg aws.Config, hostedZoneID string) (records []types.ResourceRecordSet, err error) {
	client := route53.NewFromConfig(cfg)

	rs := make([]types.ResourceRecordSet, 0)

	var nextr *string
	for {
		input := &route53.ListResourceRecordSetsInput{
			HostedZoneId:    aws.String(hostedZoneID),
			StartRecordName: nextr,
		}
		result, err := client.ListResourceRecordSets(ctx, input)
		if err != nil {
			return nil, err
		}

		rs = append(rs, result.ResourceRecordSets...)

		if result.NextRecordName == nil {
			break
		}
		nextr = result.NextRecordName
	}

	return rs, nil
}

// DeleteRecord deletes a record in a hosted zone.
func DeleteRecord(ctx context.Context, cfg aws.Config, hostedZoneID string, record types.ResourceRecordSet) error {
	client := route53.NewFromConfig(cfg)

	input := &route53.ChangeResourceRecordSetsInput{
		HostedZoneId: aws.String(hostedZoneID),
		ChangeBatch: &types.ChangeBatch{
			Changes: []types.Change{
				{
					Action:            types.ChangeActionDelete,
					ResourceRecordSet: &record,
				},
			},
		},
	}

	_, err := client.ChangeResourceRecordSets(ctx, input)
	if err != nil {
		return err
	}

	return nil
}
