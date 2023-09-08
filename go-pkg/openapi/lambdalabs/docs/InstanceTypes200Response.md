# InstanceTypes200Response

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Data** | [**map[string]InstanceTypes200ResponseDataValue**](InstanceTypes200ResponseDataValue.md) | Dict of instance_type_name to instance_type and region availability. | 

## Methods

### NewInstanceTypes200Response

`func NewInstanceTypes200Response(data map[string]InstanceTypes200ResponseDataValue, ) *InstanceTypes200Response`

NewInstanceTypes200Response instantiates a new InstanceTypes200Response object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewInstanceTypes200ResponseWithDefaults

`func NewInstanceTypes200ResponseWithDefaults() *InstanceTypes200Response`

NewInstanceTypes200ResponseWithDefaults instantiates a new InstanceTypes200Response object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetData

`func (o *InstanceTypes200Response) GetData() map[string]InstanceTypes200ResponseDataValue`

GetData returns the Data field if non-nil, zero value otherwise.

### GetDataOk

`func (o *InstanceTypes200Response) GetDataOk() (*map[string]InstanceTypes200ResponseDataValue, bool)`

GetDataOk returns a tuple with the Data field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetData

`func (o *InstanceTypes200Response) SetData(v map[string]InstanceTypes200ResponseDataValue)`

SetData sets Data field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


