package git

import (
	"log"
	"os"

	git "github.com/go-git/go-git/v5"
	"github.com/go-git/go-git/v5/plumbing/transport/http"
)

var (
	// TODO: use env vars and update token
	username = "leptoninfra"
	token    = "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"
)

// TODO: add branch and tag support
func Clone(dir, url string) error {
	_, err := git.PlainClone(dir, false, &git.CloneOptions{
		// The intended use of a GitHub personal access token is in replace of your password
		// because access tokens can easily be revoked.
		// https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/
		Auth: &http.BasicAuth{
			Username: username, // yes, this can be anything except an empty string
			Password: token,
		},
		URL:      url,
		Progress: os.Stdout,
	})
	if err != nil {
		return err
	}
	log.Printf("Git Cloned: %s\n", url)
	return nil
}
