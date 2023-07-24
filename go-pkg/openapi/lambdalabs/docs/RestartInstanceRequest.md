# RestartInstanceRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**InstanceIds** | **[]string** | The unique identifiers (IDs) of the instances to restart | 

## Methods

### NewRestartInstanceRequest

`func NewRestartInstanceRequest(instanceIds []string, ) *RestartInstanceRequest`

NewRestartInstanceRequest instantiates a new RestartInstanceRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewRestartInstanceRequestWithDefaults

`func NewRestartInstanceRequestWithDefaults() *RestartInstanceRequest`

NewRestartInstanceRequestWithDefaults instantiates a new RestartInstanceRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetInstanceIds

`func (o *RestartInstanceRequest) GetInstanceIds() []string`

GetInstanceIds returns the InstanceIds field if non-nil, zero value otherwise.

### GetInstanceIdsOk

`func (o *RestartInstanceRequest) GetInstanceIdsOk() (*[]string, bool)`

GetInstanceIdsOk returns a tuple with the InstanceIds field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetInstanceIds

`func (o *RestartInstanceRequest) SetInstanceIds(v []string)`

SetInstanceIds sets InstanceIds field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

