# InstanceTypeSpecs

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Vcpus** | **int32** | Number of virtual CPUs | 
**MemoryGib** | **int32** | Amount of RAM, in gibibytes (GiB) | 
**StorageGib** | **int32** | Amount of storage, in gibibytes (GiB). | 

## Methods

### NewInstanceTypeSpecs

`func NewInstanceTypeSpecs(vcpus int32, memoryGib int32, storageGib int32, ) *InstanceTypeSpecs`

NewInstanceTypeSpecs instantiates a new InstanceTypeSpecs object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewInstanceTypeSpecsWithDefaults

`func NewInstanceTypeSpecsWithDefaults() *InstanceTypeSpecs`

NewInstanceTypeSpecsWithDefaults instantiates a new InstanceTypeSpecs object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetVcpus

`func (o *InstanceTypeSpecs) GetVcpus() int32`

GetVcpus returns the Vcpus field if non-nil, zero value otherwise.

### GetVcpusOk

`func (o *InstanceTypeSpecs) GetVcpusOk() (*int32, bool)`

GetVcpusOk returns a tuple with the Vcpus field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetVcpus

`func (o *InstanceTypeSpecs) SetVcpus(v int32)`

SetVcpus sets Vcpus field to given value.


### GetMemoryGib

`func (o *InstanceTypeSpecs) GetMemoryGib() int32`

GetMemoryGib returns the MemoryGib field if non-nil, zero value otherwise.

### GetMemoryGibOk

`func (o *InstanceTypeSpecs) GetMemoryGibOk() (*int32, bool)`

GetMemoryGibOk returns a tuple with the MemoryGib field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMemoryGib

`func (o *InstanceTypeSpecs) SetMemoryGib(v int32)`

SetMemoryGib sets MemoryGib field to given value.


### GetStorageGib

`func (o *InstanceTypeSpecs) GetStorageGib() int32`

GetStorageGib returns the StorageGib field if non-nil, zero value otherwise.

### GetStorageGibOk

`func (o *InstanceTypeSpecs) GetStorageGibOk() (*int32, bool)`

GetStorageGibOk returns a tuple with the StorageGib field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStorageGib

`func (o *InstanceTypeSpecs) SetStorageGib(v int32)`

SetStorageGib sets StorageGib field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


