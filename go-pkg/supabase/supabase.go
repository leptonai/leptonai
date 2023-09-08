package supabase

import (
	"database/sql"
	"fmt"
	"os"

	goutil "github.com/leptonai/lepton/go-pkg/util"
)

const (
	DefaultHost   = "db.syiiuiockdgfcdldqsis.supabase.co"
	DefaultDriver = "postgres"
	DefaultDBName = "postgres"
	DefaultPort   = 5432
	DefaultUser   = "postgres"
)

type SupabaseConfig struct {
	Host         string
	DBDriverName string
	DBName       string
	Port         int
	User         string
	Password     string
}

func NewConfig(host string, dbname string, driver string, port int, user string, password string) SupabaseConfig {
	return SupabaseConfig{
		Host:         host,
		DBDriverName: driver,
		DBName:       dbname,
		Port:         port,
		User:         user,
		Password:     password,
	}
}

func NewDeploymentDefaultConfig(password string) SupabaseConfig {
	return SupabaseConfig{
		Host:         DefaultHost,
		DBDriverName: DefaultDriver,
		DBName:       DefaultDBName,
		Port:         DefaultPort,
		User:         DefaultUser,
		Password:     password,
	}
}

func NewDefaultConfigFromFlagAndEnv(passwordFlag string) SupabaseConfig {
	pass, found := os.LookupEnv("SUPABASE_PASSWORD")
	if passwordFlag == "" && !found {
		goutil.Logger.Fatal("No --passwordFlag set, and SUPABASE_PASSWORD env var not found")
	}
	// flag overwrites env var
	if passwordFlag != "" {
		pass = passwordFlag
	}
	return SupabaseConfig{
		Host:         DefaultHost,
		DBDriverName: DefaultDriver,
		DBName:       DefaultDBName,
		Port:         DefaultPort,
		User:         DefaultUser,
		Password:     pass,
	}
}

func (c SupabaseConfig) DSN() string {
	return fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s",
		c.Host, c.Port, c.User, c.Password, c.DBName,
	)
}

func (c SupabaseConfig) NewHandler() (*sql.DB, error) {
	dsn := c.DSN()
	db, err := sql.Open(c.DBDriverName, dsn)
	if err != nil {
		return nil, fmt.Errorf("NewHandler: failed to open database %v", err)
	}
	if err = db.Ping(); err != nil {
		return nil, fmt.Errorf("NewHandler: failed to ping database %v", err)
	}
	return db, nil
}
