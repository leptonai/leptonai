package kms

import (
	"context"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/kms"
	"github.com/aws/aws-sdk-go-v2/service/kms/types"
)

// ListAliases lists all aliases.
func ListAliases(ctx context.Context, cfg aws.Config) ([]types.AliasListEntry, error) {
	as := make([]types.AliasListEntry, 0)

	client := kms.NewFromConfig(cfg)
	marker := ""
	for {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		input := &kms.ListAliasesInput{}
		if marker != "" {
			input.Marker = &marker
		}
		aliases, err := client.ListAliases(ctx, input)
		if err != nil {
			return nil, err
		}

		as = append(as, aliases.Aliases...)

		if !aliases.Truncated {
			break
		}

		marker = *aliases.NextMarker
	}

	return as, nil
}

// ScheduleDeleteKeyByID deletes a key by ID with a 7 day schedule.
func ScheduleDeleteKeyByID(ctx context.Context, cfg aws.Config, id *string) error {
	var purgePendingWindowInDays int32 = 7

	client := kms.NewFromConfig(cfg)

	_, err := client.ScheduleKeyDeletion(ctx, &kms.ScheduleKeyDeletionInput{
		KeyId:               id,
		PendingWindowInDays: &purgePendingWindowInDays,
	})

	return err
}
