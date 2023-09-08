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

// checks if the TerminateInstance200ResponseData type satisfies the MappedNullable interface at compile time
var _ MappedNullable = &TerminateInstance200ResponseData{}

// TerminateInstance200ResponseData struct for TerminateInstance200ResponseData
type TerminateInstance200ResponseData struct {
	// List of instances that were terminated. Note: this list might not contain all instances requested to be terminated.
	TerminatedInstances []Instance `json:"terminated_instances"`
}

// NewTerminateInstance200ResponseData instantiates a new TerminateInstance200ResponseData object
// This constructor will assign default values to properties that have it defined,
// and makes sure properties required by API are set, but the set of arguments
// will change when the set of required properties is changed
func NewTerminateInstance200ResponseData(terminatedInstances []Instance) *TerminateInstance200ResponseData {
	this := TerminateInstance200ResponseData{}
	this.TerminatedInstances = terminatedInstances
	return &this
}

// NewTerminateInstance200ResponseDataWithDefaults instantiates a new TerminateInstance200ResponseData object
// This constructor will only assign default values to properties that have it defined,
// but it doesn't guarantee that properties required by API are set
func NewTerminateInstance200ResponseDataWithDefaults() *TerminateInstance200ResponseData {
	this := TerminateInstance200ResponseData{}
	return &this
}

// GetTerminatedInstances returns the TerminatedInstances field value
func (o *TerminateInstance200ResponseData) GetTerminatedInstances() []Instance {
	if o == nil {
		var ret []Instance
		return ret
	}

	return o.TerminatedInstances
}

// GetTerminatedInstancesOk returns a tuple with the TerminatedInstances field value
// and a boolean to check if the value has been set.
func (o *TerminateInstance200ResponseData) GetTerminatedInstancesOk() ([]Instance, bool) {
	if o == nil {
		return nil, false
	}
	return o.TerminatedInstances, true
}

// SetTerminatedInstances sets field value
func (o *TerminateInstance200ResponseData) SetTerminatedInstances(v []Instance) {
	o.TerminatedInstances = v
}

func (o TerminateInstance200ResponseData) MarshalJSON() ([]byte, error) {
	toSerialize,err := o.ToMap()
	if err != nil {
		return []byte{}, err
	}
	return json.Marshal(toSerialize)
}

func (o TerminateInstance200ResponseData) ToMap() (map[string]interface{}, error) {
	toSerialize := map[string]interface{}{}
	toSerialize["terminated_instances"] = o.TerminatedInstances
	return toSerialize, nil
}

type NullableTerminateInstance200ResponseData struct {
	value *TerminateInstance200ResponseData
	isSet bool
}

func (v NullableTerminateInstance200ResponseData) Get() *TerminateInstance200ResponseData {
	return v.value
}

func (v *NullableTerminateInstance200ResponseData) Set(val *TerminateInstance200ResponseData) {
	v.value = val
	v.isSet = true
}

func (v NullableTerminateInstance200ResponseData) IsSet() bool {
	return v.isSet
}

func (v *NullableTerminateInstance200ResponseData) Unset() {
	v.value = nil
	v.isSet = false
}

func NewNullableTerminateInstance200ResponseData(val *TerminateInstance200ResponseData) *NullableTerminateInstance200ResponseData {
	return &NullableTerminateInstance200ResponseData{value: val, isSet: true}
}

func (v NullableTerminateInstance200ResponseData) MarshalJSON() ([]byte, error) {
	return json.Marshal(v.value)
}

func (v *NullableTerminateInstance200ResponseData) UnmarshalJSON(src []byte) error {
	v.isSet = true
	return json.Unmarshal(src, &v.value)
}


