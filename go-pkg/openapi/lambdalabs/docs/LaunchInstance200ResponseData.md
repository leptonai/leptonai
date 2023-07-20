# LaunchInstance200ResponseData

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**InstanceIds** | **[]string** | The unique identifiers (IDs) of the launched instances. Note: if a quantity was specified, fewer than the requested quantity might have been launched. | 

## Methods

### NewLaunchInstance200ResponseData

`func NewLaunchInstance200ResponseData(instanceIds []string, ) *LaunchInstance200ResponseData`

NewLaunchInstance200ResponseData instantiates a new LaunchInstance200ResponseData object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewLaunchInstance200ResponseDataWithDefaults

`func NewLaunchInstance200ResponseDataWithDefaults() *LaunchInstance200ResponseData`

NewLaunchInstance200ResponseDataWithDefaults instantiates a new LaunchInstance200ResponseData object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetInstanceIds

`func (o *LaunchInstance200ResponseData) GetInstanceIds() []string`

GetInstanceIds returns the InstanceIds field if non-nil, zero value otherwise.

### GetInstanceIdsOk

`func (o *LaunchInstance200ResponseData) GetInstanceIdsOk() (*[]string, bool)`

GetInstanceIdsOk returns a tuple with the InstanceIds field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetInstanceIds

`func (o *LaunchInstance200ResponseData) SetInstanceIds(v []string)`

SetInstanceIds sets InstanceIds field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


