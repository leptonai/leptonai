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

// checks if the AddSSHKeyRequest type satisfies the MappedNullable interface at compile time
var _ MappedNullable = &AddSSHKeyRequest{}

// AddSSHKeyRequest The name for the SSH key. Optionally, an existing public key can be supplied for the `public_key` property. If the `public_key` property is omitted, a new key pair is generated. The private key is returned in the response.
type AddSSHKeyRequest struct {
	// Name of the SSH key
	Name string `json:"name"`
	// Public key for the SSH key
	PublicKey *string `json:"public_key,omitempty"`
}

// NewAddSSHKeyRequest instantiates a new AddSSHKeyRequest object
// This constructor will assign default values to properties that have it defined,
// and makes sure properties required by API are set, but the set of arguments
// will change when the set of required properties is changed
func NewAddSSHKeyRequest(name string) *AddSSHKeyRequest {
	this := AddSSHKeyRequest{}
	this.Name = name
	return &this
}

// NewAddSSHKeyRequestWithDefaults instantiates a new AddSSHKeyRequest object
// This constructor will only assign default values to properties that have it defined,
// but it doesn't guarantee that properties required by API are set
func NewAddSSHKeyRequestWithDefaults() *AddSSHKeyRequest {
	this := AddSSHKeyRequest{}
	return &this
}

// GetName returns the Name field value
func (o *AddSSHKeyRequest) GetName() string {
	if o == nil {
		var ret string
		return ret
	}

	return o.Name
}

// GetNameOk returns a tuple with the Name field value
// and a boolean to check if the value has been set.
func (o *AddSSHKeyRequest) GetNameOk() (*string, bool) {
	if o == nil {
		return nil, false
	}
	return &o.Name, true
}

// SetName sets field value
func (o *AddSSHKeyRequest) SetName(v string) {
	o.Name = v
}

// GetPublicKey returns the PublicKey field value if set, zero value otherwise.
func (o *AddSSHKeyRequest) GetPublicKey() string {
	if o == nil || IsNil(o.PublicKey) {
		var ret string
		return ret
	}
	return *o.PublicKey
}

// GetPublicKeyOk returns a tuple with the PublicKey field value if set, nil otherwise
// and a boolean to check if the value has been set.
func (o *AddSSHKeyRequest) GetPublicKeyOk() (*string, bool) {
	if o == nil || IsNil(o.PublicKey) {
		return nil, false
	}
	return o.PublicKey, true
}

// HasPublicKey returns a boolean if a field has been set.
func (o *AddSSHKeyRequest) HasPublicKey() bool {
	if o != nil && !IsNil(o.PublicKey) {
		return true
	}

	return false
}

// SetPublicKey gets a reference to the given string and assigns it to the PublicKey field.
func (o *AddSSHKeyRequest) SetPublicKey(v string) {
	o.PublicKey = &v
}

func (o AddSSHKeyRequest) MarshalJSON() ([]byte, error) {
	toSerialize,err := o.ToMap()
	if err != nil {
		return []byte{}, err
	}
	return json.Marshal(toSerialize)
}

func (o AddSSHKeyRequest) ToMap() (map[string]interface{}, error) {
	toSerialize := map[string]interface{}{}
	toSerialize["name"] = o.Name
	if !IsNil(o.PublicKey) {
		toSerialize["public_key"] = o.PublicKey
	}
	return toSerialize, nil
}

type NullableAddSSHKeyRequest struct {
	value *AddSSHKeyRequest
	isSet bool
}

func (v NullableAddSSHKeyRequest) Get() *AddSSHKeyRequest {
	return v.value
}

func (v *NullableAddSSHKeyRequest) Set(val *AddSSHKeyRequest) {
	v.value = val
	v.isSet = true
}

func (v NullableAddSSHKeyRequest) IsSet() bool {
	return v.isSet
}

func (v *NullableAddSSHKeyRequest) Unset() {
	v.value = nil
	v.isSet = false
}

func NewNullableAddSSHKeyRequest(val *AddSSHKeyRequest) *NullableAddSSHKeyRequest {
	return &NullableAddSSHKeyRequest{value: val, isSet: true}
}

func (v NullableAddSSHKeyRequest) MarshalJSON() ([]byte, error) {
	return json.Marshal(v.value)
}

func (v *NullableAddSSHKeyRequest) UnmarshalJSON(src []byte) error {
	v.isSet = true
	return json.Unmarshal(src, &v.value)
}

