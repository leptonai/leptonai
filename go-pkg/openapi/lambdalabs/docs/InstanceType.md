# InstanceType

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Name** | **string** | Name of an instance type | 
**Description** | **string** | Long name of the instance type | 
**PriceCentsPerHour** | **int32** | Price of the instance type, in US cents per hour | 
**Specs** | [**InstanceTypeSpecs**](InstanceTypeSpecs.md) |  | 

## Methods

### NewInstanceType

`func NewInstanceType(name string, description string, priceCentsPerHour int32, specs InstanceTypeSpecs, ) *InstanceType`

NewInstanceType instantiates a new InstanceType object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewInstanceTypeWithDefaults

`func NewInstanceTypeWithDefaults() *InstanceType`

NewInstanceTypeWithDefaults instantiates a new InstanceType object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetName

`func (o *InstanceType) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *InstanceType) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *InstanceType) SetName(v string)`

SetName sets Name field to given value.


### GetDescription

`func (o *InstanceType) GetDescription() string`

GetDescription returns the Description field if non-nil, zero value otherwise.

### GetDescriptionOk

`func (o *InstanceType) GetDescriptionOk() (*string, bool)`

GetDescriptionOk returns a tuple with the Description field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDescription

`func (o *InstanceType) SetDescription(v string)`

SetDescription sets Description field to given value.


### GetPriceCentsPerHour

`func (o *InstanceType) GetPriceCentsPerHour() int32`

GetPriceCentsPerHour returns the PriceCentsPerHour field if non-nil, zero value otherwise.

### GetPriceCentsPerHourOk

`func (o *InstanceType) GetPriceCentsPerHourOk() (*int32, bool)`

GetPriceCentsPerHourOk returns a tuple with the PriceCentsPerHour field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPriceCentsPerHour

`func (o *InstanceType) SetPriceCentsPerHour(v int32)`

SetPriceCentsPerHour sets PriceCentsPerHour field to given value.


### GetSpecs

`func (o *InstanceType) GetSpecs() InstanceTypeSpecs`

GetSpecs returns the Specs field if non-nil, zero value otherwise.

### GetSpecsOk

`func (o *InstanceType) GetSpecsOk() (*InstanceTypeSpecs, bool)`

GetSpecsOk returns a tuple with the Specs field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSpecs

`func (o *InstanceType) SetSpecs(v InstanceTypeSpecs)`

SetSpecs sets Specs field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


