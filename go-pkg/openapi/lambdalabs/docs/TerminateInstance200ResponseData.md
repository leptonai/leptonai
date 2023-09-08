# TerminateInstance200ResponseData

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**TerminatedInstances** | [**[]Instance**](Instance.md) | List of instances that were terminated. Note: this list might not contain all instances requested to be terminated. | 

## Methods

### NewTerminateInstance200ResponseData

`func NewTerminateInstance200ResponseData(terminatedInstances []Instance, ) *TerminateInstance200ResponseData`

NewTerminateInstance200ResponseData instantiates a new TerminateInstance200ResponseData object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewTerminateInstance200ResponseDataWithDefaults

`func NewTerminateInstance200ResponseDataWithDefaults() *TerminateInstance200ResponseData`

NewTerminateInstance200ResponseDataWithDefaults instantiates a new TerminateInstance200ResponseData object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetTerminatedInstances

`func (o *TerminateInstance200ResponseData) GetTerminatedInstances() []Instance`

GetTerminatedInstances returns the TerminatedInstances field if non-nil, zero value otherwise.

### GetTerminatedInstancesOk

`func (o *TerminateInstance200ResponseData) GetTerminatedInstancesOk() (*[]Instance, bool)`

GetTerminatedInstancesOk returns a tuple with the TerminatedInstances field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTerminatedInstances

`func (o *TerminateInstance200ResponseData) SetTerminatedInstances(v []Instance)`

SetTerminatedInstances sets TerminatedInstances field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


