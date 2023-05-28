package namedb

import (
	"fmt"
	"testing"
)

type TestStruct struct {
	Name    string
	ID      string
	Version int64
}

func (t TestStruct) GetName() string {
	return t.Name
}

func (t TestStruct) GetID() string {
	return t.ID
}

func (t TestStruct) GetVersion() int64 {
	return t.Version
}

func TestNewNameDB(t *testing.T) {
	db := NewNameDB[TestStruct]()
	if db == nil {
		t.Error("NewNameDB[TestStruct]() returned nil")
	}
}

func TestAdd(t *testing.T) {
	db := NewNameDB[TestStruct]()
	db.Add(&TestStruct{Name: "test", ID: "test", Version: 1})
	if len(db.dataByID) != 1 {
		t.Errorf("db.dataByID has length %d, expected 1", len(db.dataByID))
	}
	if len(db.dataByName) != 1 {
		t.Errorf("db.dataByName has length %d, expected 1", len(db.dataByName))
	}
	if len(db.dataByName["test"]) != 1 {
		t.Errorf("db.dataByName[\"test\"] has length %d, expected 1", len(db.dataByName["test"]))
	}
}

func TestGetByID(t *testing.T) {
	db := NewNameDB[TestStruct]()
	db.Add(&TestStruct{Name: "test", ID: "test", Version: 1})
	if db.GetByID("test") == nil {
		t.Error("db.GetByID(\"test\") returned nil")
	}
}

func TestGetByName(t *testing.T) {
	db := NewNameDB[TestStruct]()
	db.Add(&TestStruct{Name: "test", ID: "test", Version: 1})
	if len(db.GetByName("test")) != 1 {
		t.Errorf("db.GetByName(\"test\") returned length %d, expected 1", len(db.GetByName("test")))
	}
}

func TestGetByNameEmpty(t *testing.T) {
	db := NewNameDB[TestStruct]()
	if db.GetByName("test") != nil {
		t.Errorf("db.GetByName(\"test\") returned %v, expected nil", db.GetByName("test"))
	}
}

func TestGetByNameMultiple(t *testing.T) {
	db := NewNameDB[TestStruct]()
	db.Add(&TestStruct{Name: "test", ID: "test", Version: 1})
	db.Add(&TestStruct{Name: "test", ID: "test2", Version: 2})
	if len(db.GetByName("test")) != 2 {
		t.Errorf("db.GetByName(\"test\") returned length %d, expected 2", len(db.GetByName("test")))
	}
}

func TestGetByNameMultipleVersion(t *testing.T) {
	db := NewNameDB[TestStruct]()
	db.Add(&TestStruct{Name: "test", ID: "test", Version: 1})
	db.Add(&TestStruct{Name: "test", ID: "test2", Version: 2})
	if db.GetByName("test")[0].GetVersion() != 2 {
		t.Errorf("db.GetByName(\"test\")[0].GetVersion() returned %d, expected 2", db.GetByName("test")[0].GetVersion())
	}
}

func TestGetByNameMultipleVersion2(t *testing.T) {
	db := NewNameDB[TestStruct]()
	db.Add(&TestStruct{Name: "test", ID: "test", Version: 1})
	db.Add(&TestStruct{Name: "test", ID: "test2", Version: 2})
	if db.GetByName("test")[1].GetVersion() != 1 {
		t.Errorf("db.GetByName(\"test\")[1].GetVersion() returned %d, expected 1", db.GetByName("test")[1].GetVersion())
	}
}

func TestGetByNameMultipleVersion3(t *testing.T) {
	db := NewNameDB[TestStruct]()
	db.Add(&TestStruct{Name: "test", ID: "test", Version: 1})
	db.Add(&TestStruct{Name: "test", ID: "test", Version: 2})
	if db.GetByName("test")[0].GetVersion() != 2 {
		t.Errorf("db.GetByName(\"test\")[0].GetVersion() returned %d, expected 2", db.GetByName("test")[0].GetVersion())
	}
	if db.GetByName("test")[1].GetVersion() != 1 {
		t.Errorf("db.GetByName(\"test\")[1].GetVersion() returned %d, expected 1", db.GetByName("test")[1].GetVersion())
	}
}

func TestGetLatestByName(t *testing.T) {
	db := NewNameDB[TestStruct]()
	db.Add(&TestStruct{Name: "test", ID: "test", Version: 1})
	db.Add(&TestStruct{Name: "test", ID: "test2", Version: 2})
	if db.GetLatestByName("test").GetVersion() != 2 {
		t.Errorf("db.GetLatestByName(\"test\").GetVersion() returned %d, expected 2", db.GetLatestByName("test").GetVersion())
	}
}

func TestGetLatestByNameEmpty(t *testing.T) {
	db := NewNameDB[TestStruct]()
	if db.GetLatestByName("test") != nil {
		t.Errorf("db.GetLatestByName(\"test\") returned %v, expected nil", db.GetLatestByName("test"))
	}
}

func TestGetLatestByNameMultiple(t *testing.T) {
	db := NewNameDB[TestStruct]()
	db.Add(&TestStruct{Name: "test", ID: "test", Version: 1})
	db.Add(&TestStruct{Name: "test", ID: "test2", Version: 2})
	if db.GetLatestByName("test").GetVersion() != 2 {
		t.Errorf("db.GetLatestByName(\"test\").GetVersion() returned %d, expected 2", db.GetLatestByName("test").GetVersion())
	}
}

func TestDelete(t *testing.T) {
	db := NewNameDB[TestStruct]()
	db.Add(&TestStruct{Name: "test", ID: "test", Version: 1})
	db.Delete(&TestStruct{Name: "test", ID: "test", Version: 1})
	if len(db.dataByID) != 0 {
		t.Errorf("db.dataByID has length %d, expected 0", len(db.dataByID))
	}
	if len(db.dataByName["test"]) != 0 {
		t.Errorf("db.dataByName has length %d, expected 0", len(db.dataByName["test"]))
	}
}

func TestDeleteMultiple(t *testing.T) {
	db := NewNameDB[TestStruct]()
	db.Add(&TestStruct{Name: "test", ID: "test", Version: 1})
	db.Add(&TestStruct{Name: "test", ID: "test2", Version: 2})
	db.Delete(&TestStruct{Name: "test", ID: "test", Version: 1})
	if len(db.dataByID) != 1 {
		t.Errorf("db.dataByID has length %d, expected 1", len(db.dataByID))
	}
	fmt.Printf("%+v\n", db.dataByID)
	fmt.Printf("%+v\n", db.dataByName)
	if len(db.dataByName) != 1 {
		t.Errorf("db.dataByName has length %d, expected 1", len(db.dataByName))
	}
	if len(db.dataByName["test"]) != 1 {
		t.Errorf("db.dataByName[\"test\"] has length %d, expected 1", len(db.dataByName["test"]))
	}
}

func TestDeleteByID(t *testing.T) {
	db := NewNameDB[TestStruct]()
	db.Add(&TestStruct{Name: "test", ID: "test", Version: 1})
	db.DeleteByID("test")
	if len(db.dataByID) != 0 {
		t.Errorf("db.dataByID has length %d, expected 0", len(db.dataByID))
	}
	if len(db.dataByName["test"]) != 0 {
		t.Errorf("db.dataByName has length %d, expected 0", len(db.dataByName["test"]))
	}
}

func TestDeleteByName(t *testing.T) {
	db := NewNameDB[TestStruct]()
	db.Add(&TestStruct{Name: "test", ID: "test", Version: 1})
	db.DeleteByName("test")
	if len(db.dataByID) != 0 {
		t.Errorf("db.dataByID has length %d, expected 0", len(db.dataByID))
	}
	if len(db.dataByName) != 0 {
		t.Errorf("db.dataByName has length %d, expected 0", len(db.dataByName))
	}
}

func TestGetAll(t *testing.T) {
	db := NewNameDB[TestStruct]()
	db.Add(&TestStruct{Name: "test", ID: "test", Version: 1})
	if len(db.GetAll()) != 1 {
		t.Errorf("db.GetAll() has length %d, expected 1", len(db.GetAll()))
	}
}
