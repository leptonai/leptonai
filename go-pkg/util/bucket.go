package util

import (
	"context"
	"fmt"

	"gocloud.dev/blob"
)

// MustOpenAndAccessBucket opens a bucket and checks if it is accessible.
// TODO: add test
func MustOpenAndAccessBucket(ctx context.Context, typ, name, region, prefix string) *blob.Bucket {
	bu, err := blob.OpenBucket(
		ctx,
		fmt.Sprintf("%s://%s?region=%s&prefix=%s/", typ, name, region, prefix),
	)

	if err != nil {
		Logger.Fatalw("failed to open bucket",
			"operation", "openBucket",
			"bucketType", typ,
			"bucketName", name,
			"region", region,
			"prefix", prefix,
			"error", err,
		)
	}

	ok, err := bu.IsAccessible(context.Background())
	if err != nil {
		Logger.Fatalw("failed to access bucket",
			"operation", "openBucket",
			"bucketType", typ,
			"bucketName", name,
			"region", region,
			"prefix", prefix,
			"error", err,
		)
	}

	if !ok {
		Logger.Fatalw("cannot access bucket",
			"operation", "openBucket",
			"bucketType", typ,
			"bucketName", name,
			"region", region,
			"prefix", prefix,
			"error", err,
		)
	}

	return bu
}
