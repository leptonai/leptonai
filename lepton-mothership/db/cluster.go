package db

import (
	"errors"
	"sync"
)

// DataStore represents an in-memory data store using a map
// TODO: replace this with a real database with persistence
type DataStore struct {
	data map[string]interface{}
	mu   sync.Mutex
}

// NewDataStore creates a new instance of DataStore
func NewDataStore() *DataStore {
	return &DataStore{
		data: make(map[string]interface{}),
	}
}

// Get retrieves the value associated with the given key from the data store
func (ds *DataStore) Get(key string) (interface{}, error) {
	ds.mu.Lock()
	defer ds.mu.Unlock()

	val, ok := ds.data[key]
	if !ok {
		return nil, errors.New("key not found")
	}
	return val, nil
}

// List returns a slice of all values in the data store
func (ds *DataStore) List() ([]interface{}, error) {
	ds.mu.Lock()
	defer ds.mu.Unlock()

	values := make([]interface{}, 0, len(ds.data))
	for _, val := range ds.data {
		values = append(values, val)
	}
	return values, nil
}

// Delete removes the value associated with the given key from the data store
func (ds *DataStore) Delete(key string) error {
	ds.mu.Lock()
	defer ds.mu.Unlock()

	delete(ds.data, key)
	return nil
}

// Create adds a new value with the given key to the data store
func (ds *DataStore) Create(key string, value interface{}) error {
	ds.mu.Lock()
	defer ds.mu.Unlock()

	if _, ok := ds.data[key]; ok {
		return errors.New("key already exists")
	}
	ds.data[key] = value
	return nil
}

// Update updates the value associated with the given key in the data store
func (ds *DataStore) Update(key string, value interface{}) error {
	ds.mu.Lock()
	defer ds.mu.Unlock()

	if _, ok := ds.data[key]; !ok {
		return errors.New("key not found")
	}
	ds.data[key] = value
	return nil
}
