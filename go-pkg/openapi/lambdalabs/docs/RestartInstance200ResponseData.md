# RestartInstance200ResponseData

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**RestartedInstances** | [**[]Instance**](Instance.md) | List of instances that were restarted. Note: this list might not contain all instances requested to be restarted. | 

## Methods

### NewRestartInstance200ResponseData

`func NewRestartInstance200ResponseData(restartedInstances []Instance, ) *RestartInstance200ResponseData`

NewRestartInstance200ResponseData instantiates a new RestartInstance200ResponseData object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewRestartInstance200ResponseDataWithDefaults

`func NewRestartInstance200ResponseDataWithDefaults() *RestartInstance200ResponseData`

NewRestartInstance200ResponseDataWithDefaults instantiates a new RestartInstance200ResponseData object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetRestartedInstances

`func (o *RestartInstance200ResponseData) GetRestartedInstances() []Instance`

GetRestartedInstances returns the RestartedInstances field if non-nil, zero value otherwise.

### GetRestartedInstancesOk

`func (o *RestartInstance200ResponseData) GetRestartedInstancesOk() (*[]Instance, bool)`

GetRestartedInstancesOk returns a tuple with the RestartedInstances field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRestartedInstances

`func (o *RestartInstance200ResponseData) SetRestartedInstances(v []Instance)`

SetRestartedInstances sets RestartedInstances field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


