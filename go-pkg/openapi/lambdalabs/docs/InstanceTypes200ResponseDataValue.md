# InstanceTypes200ResponseDataValue

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**InstanceType** | [**InstanceType**](InstanceType.md) |  | 
**RegionsWithCapacityAvailable** | [**[]Region**](Region.md) | List of regions, if any, that have this instance type available | 

## Methods

### NewInstanceTypes200ResponseDataValue

`func NewInstanceTypes200ResponseDataValue(instanceType InstanceType, regionsWithCapacityAvailable []Region, ) *InstanceTypes200ResponseDataValue`

NewInstanceTypes200ResponseDataValue instantiates a new InstanceTypes200ResponseDataValue object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewInstanceTypes200ResponseDataValueWithDefaults

`func NewInstanceTypes200ResponseDataValueWithDefaults() *InstanceTypes200ResponseDataValue`

NewInstanceTypes200ResponseDataValueWithDefaults instantiates a new InstanceTypes200ResponseDataValue object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetInstanceType

`func (o *InstanceTypes200ResponseDataValue) GetInstanceType() InstanceType`

GetInstanceType returns the InstanceType field if non-nil, zero value otherwise.

### GetInstanceTypeOk

`func (o *InstanceTypes200ResponseDataValue) GetInstanceTypeOk() (*InstanceType, bool)`

GetInstanceTypeOk returns a tuple with the InstanceType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetInstanceType

`func (o *InstanceTypes200ResponseDataValue) SetInstanceType(v InstanceType)`

SetInstanceType sets InstanceType field to given value.


### GetRegionsWithCapacityAvailable

`func (o *InstanceTypes200ResponseDataValue) GetRegionsWithCapacityAvailable() []Region`

GetRegionsWithCapacityAvailable returns the RegionsWithCapacityAvailable field if non-nil, zero value otherwise.

### GetRegionsWithCapacityAvailableOk

`func (o *InstanceTypes200ResponseDataValue) GetRegionsWithCapacityAvailableOk() (*[]Region, bool)`

GetRegionsWithCapacityAvailableOk returns a tuple with the RegionsWithCapacityAvailable field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRegionsWithCapacityAvailable

`func (o *InstanceTypes200ResponseDataValue) SetRegionsWithCapacityAvailable(v []Region)`

SetRegionsWithCapacityAvailable sets RegionsWithCapacityAvailable field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


