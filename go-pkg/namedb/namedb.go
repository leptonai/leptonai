package namedb

import (
	"math"
	"sort"
	"sync"
)

type Data interface {
	GetName() string
	GetID() string
	GetVersion() int64
}

type NameDB[T Data] struct {
	dataByID   map[string]*T
	dataByName map[string]map[int64]*T
	lock       *sync.RWMutex
}

func NewNameDB[T Data]() *NameDB[T] {
	return &NameDB[T]{
		dataByID:   make(map[string]*T),
		dataByName: make(map[string]map[int64]*T),
		lock:       &sync.RWMutex{},
	}
}

func (db *NameDB[T]) Add(ts ...*T) {
	db.lock.Lock()
	defer db.lock.Unlock()
	for _, t := range ts {
		if t == nil {
			continue
		}
		// if there is already an object of the same version in the db, delete it
		if old, ok := db.dataByName[(*t).GetName()][(*t).GetVersion()]; ok {
			delete(db.dataByID, (*old).GetID())
		}
		if db.dataByName[(*t).GetName()] == nil {
			db.dataByName[(*t).GetName()] = make(map[int64]*T)
		}
		db.dataByName[(*t).GetName()][(*t).GetVersion()] = t
		db.dataByID[(*t).GetID()] = t
	}
}

func (db *NameDB[T]) GetByID(id string) *T {
	db.lock.RLock()
	defer db.lock.RUnlock()
	return db.dataByID[id]
}

func (db *NameDB[T]) GetByName(name string) []*T {
	db.lock.RLock()
	if db.dataByName[name] == nil {
		db.lock.RUnlock()
		return nil
	}
	ts := make([]*T, 0, len(db.dataByName[name]))
	for _, t := range db.dataByName[name] {
		ts = append(ts, t)
	}
	db.lock.RUnlock()
	sort.Slice(ts, func(i, j int) bool {
		return (*ts[i]).GetVersion() > (*ts[j]).GetVersion()
	})
	return ts
}

func (db *NameDB[T]) GetLatestByName(name string) *T {
	db.lock.RLock()
	defer db.lock.RUnlock()
	// len(nil map) == 0 so we don't need to check nil here
	if len(db.dataByName[name]) == 0 {
		return nil
	}
	// get max key of db.dataByName[name]
	maxVersion := int64(math.MinInt64)
	for k := range db.dataByName[name] {
		if k > maxVersion {
			maxVersion = k
		}
	}
	t := db.dataByName[name][maxVersion]
	return t
}

func (db *NameDB[T]) Delete(ts ...*T) {
	db.lock.Lock()
	defer db.lock.Unlock()
	for _, t := range ts {
		if t == nil {
			continue
		}
		delete(db.dataByName[(*t).GetName()], (*t).GetVersion())
		delete(db.dataByID, (*t).GetID())
	}
}

func (db *NameDB[T]) DeleteByID(ids ...string) {
	db.lock.Lock()
	defer db.lock.Unlock()
	for _, id := range ids {
		if t, ok := db.dataByID[id]; ok {
			delete(db.dataByName[(*t).GetName()], (*t).GetVersion())
			delete(db.dataByID, id)
		}
	}
}

func (db *NameDB[T]) DeleteByName(names ...string) {
	db.lock.Lock()
	defer db.lock.Unlock()
	for _, name := range names {
		for _, t := range db.dataByName[name] {
			delete(db.dataByID, (*t).GetID())
		}
		delete(db.dataByName, name)
	}
}

func (db *NameDB[T]) GetAll() []*T {
	db.lock.RLock()
	defer db.lock.RUnlock()
	t := make([]*T, 0, len(db.dataByID))
	for _, d := range db.dataByID {
		t = append(t, d)
	}
	return t
}
