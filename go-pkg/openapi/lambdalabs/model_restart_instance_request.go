/*
Lambda Cloud API

API for interacting with the Lambda GPU Cloud

API version: 1.4.0
*/

// Code generated by OpenAPI Generator (https://openapi-generator.tech); DO NOT EDIT.

package lambdalabs

import (
	"encoding/json"
)

// checks if the RestartInstanceRequest type satisfies the MappedNullable interface at compile time
var _ MappedNullable = &RestartInstanceRequest{}

// RestartInstanceRequest struct for RestartInstanceRequest
type RestartInstanceRequest struct {
	// The unique identifiers (IDs) of the instances to restart
	InstanceIds []string `json:"instance_ids"`
}

// NewRestartInstanceRequest instantiates a new RestartInstanceRequest object
// This constructor will assign default values to properties that have it defined,
// and makes sure properties required by API are set, but the set of arguments
// will change when the set of required properties is changed
func NewRestartInstanceRequest(instanceIds []string) *RestartInstanceRequest {
	this := RestartInstanceRequest{}
	this.InstanceIds = instanceIds
	return &this
}

// NewRestartInstanceRequestWithDefaults instantiates a new RestartInstanceRequest object
// This constructor will only assign default values to properties that have it defined,
// but it doesn't guarantee that properties required by API are set
func NewRestartInstanceRequestWithDefaults() *RestartInstanceRequest {
	this := RestartInstanceRequest{}
	return &this
}

// GetInstanceIds returns the InstanceIds field value
func (o *RestartInstanceRequest) GetInstanceIds() []string {
	if o == nil {
		var ret []string
		return ret
	}

	return o.InstanceIds
}

// GetInstanceIdsOk returns a tuple with the InstanceIds field value
// and a boolean to check if the value has been set.
func (o *RestartInstanceRequest) GetInstanceIdsOk() ([]string, bool) {
	if o == nil {
		return nil, false
	}
	return o.InstanceIds, true
}

// SetInstanceIds sets field value
func (o *RestartInstanceRequest) SetInstanceIds(v []string) {
	o.InstanceIds = v
}

func (o RestartInstanceRequest) MarshalJSON() ([]byte, error) {
	toSerialize,err := o.ToMap()
	if err != nil {
		return []byte{}, err
	}
	return json.Marshal(toSerialize)
}

func (o RestartInstanceRequest) ToMap() (map[string]interface{}, error) {
	toSerialize := map[string]interface{}{}
	toSerialize["instance_ids"] = o.InstanceIds
	return toSerialize, nil
}

type NullableRestartInstanceRequest struct {
	value *RestartInstanceRequest
	isSet bool
}

func (v NullableRestartInstanceRequest) Get() *RestartInstanceRequest {
	return v.value
}

func (v *NullableRestartInstanceRequest) Set(val *RestartInstanceRequest) {
	v.value = val
	v.isSet = true
}

func (v NullableRestartInstanceRequest) IsSet() bool {
	return v.isSet
}

func (v *NullableRestartInstanceRequest) Unset() {
	v.value = nil
	v.isSet = false
}

func NewNullableRestartInstanceRequest(val *RestartInstanceRequest) *NullableRestartInstanceRequest {
	return &NullableRestartInstanceRequest{value: val, isSet: true}
}

func (v NullableRestartInstanceRequest) MarshalJSON() ([]byte, error) {
	return json.Marshal(v.value)
}

func (v *NullableRestartInstanceRequest) UnmarshalJSON(src []byte) error {
	v.isSet = true
	return json.Unmarshal(src, &v.value)
}

