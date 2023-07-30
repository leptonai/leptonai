package httpapi

import "github.com/gin-gonic/gin"

func HandleUserList(c *gin.Context) {
}

func HandleUserCreate(c *gin.Context) {
	// create a user and assoicate it with a new lepton env
	// create a hidden api token for the user so that web can use it to talk to the server
	// todo: assoicate the user with no env or existing env
}

func HandleUserGet(c *gin.Context) {

}

func HandleUserDelete(c *gin.Context) {

}
