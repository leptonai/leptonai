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

// checks if the ErrorResponseBody type satisfies the MappedNullable interface at compile time
var _ MappedNullable = &ErrorResponseBody{}

// ErrorResponseBody struct for ErrorResponseBody
type ErrorResponseBody struct {
	Error ModelError `json:"error"`
	// Details about errors on a per-parameter basis
	FieldErrors *map[string]ModelError `json:"field_errors,omitempty"`
}

// NewErrorResponseBody instantiates a new ErrorResponseBody object
// This constructor will assign default values to properties that have it defined,
// and makes sure properties required by API are set, but the set of arguments
// will change when the set of required properties is changed
func NewErrorResponseBody(error_ ModelError) *ErrorResponseBody {
	this := ErrorResponseBody{}
	this.Error = error_
	return &this
}

// NewErrorResponseBodyWithDefaults instantiates a new ErrorResponseBody object
// This constructor will only assign default values to properties that have it defined,
// but it doesn't guarantee that properties required by API are set
func NewErrorResponseBodyWithDefaults() *ErrorResponseBody {
	this := ErrorResponseBody{}
	return &this
}

// GetError returns the Error field value
func (o *ErrorResponseBody) GetError() ModelError {
	if o == nil {
		var ret ModelError
		return ret
	}

	return o.Error
}

// GetErrorOk returns a tuple with the Error field value
// and a boolean to check if the value has been set.
func (o *ErrorResponseBody) GetErrorOk() (*ModelError, bool) {
	if o == nil {
		return nil, false
	}
	return &o.Error, true
}

// SetError sets field value
func (o *ErrorResponseBody) SetError(v ModelError) {
	o.Error = v
}

// GetFieldErrors returns the FieldErrors field value if set, zero value otherwise.
func (o *ErrorResponseBody) GetFieldErrors() map[string]ModelError {
	if o == nil || IsNil(o.FieldErrors) {
		var ret map[string]ModelError
		return ret
	}
	return *o.FieldErrors
}

// GetFieldErrorsOk returns a tuple with the FieldErrors field value if set, nil otherwise
// and a boolean to check if the value has been set.
func (o *ErrorResponseBody) GetFieldErrorsOk() (*map[string]ModelError, bool) {
	if o == nil || IsNil(o.FieldErrors) {
		return nil, false
	}
	return o.FieldErrors, true
}

// HasFieldErrors returns a boolean if a field has been set.
func (o *ErrorResponseBody) HasFieldErrors() bool {
	if o != nil && !IsNil(o.FieldErrors) {
		return true
	}

	return false
}

// SetFieldErrors gets a reference to the given map[string]ModelError and assigns it to the FieldErrors field.
func (o *ErrorResponseBody) SetFieldErrors(v map[string]ModelError) {
	o.FieldErrors = &v
}

func (o ErrorResponseBody) MarshalJSON() ([]byte, error) {
	toSerialize,err := o.ToMap()
	if err != nil {
		return []byte{}, err
	}
	return json.Marshal(toSerialize)
}

func (o ErrorResponseBody) ToMap() (map[string]interface{}, error) {
	toSerialize := map[string]interface{}{}
	toSerialize["error"] = o.Error
	if !IsNil(o.FieldErrors) {
		toSerialize["field_errors"] = o.FieldErrors
	}
	return toSerialize, nil
}

type NullableErrorResponseBody struct {
	value *ErrorResponseBody
	isSet bool
}

func (v NullableErrorResponseBody) Get() *ErrorResponseBody {
	return v.value
}

func (v *NullableErrorResponseBody) Set(val *ErrorResponseBody) {
	v.value = val
	v.isSet = true
}

func (v NullableErrorResponseBody) IsSet() bool {
	return v.isSet
}

func (v *NullableErrorResponseBody) Unset() {
	v.value = nil
	v.isSet = false
}

func NewNullableErrorResponseBody(val *ErrorResponseBody) *NullableErrorResponseBody {
	return &NullableErrorResponseBody{value: val, isSet: true}
}

func (v NullableErrorResponseBody) MarshalJSON() ([]byte, error) {
	return json.Marshal(v.value)
}

func (v *NullableErrorResponseBody) UnmarshalJSON(src []byte) error {
	v.isSet = true
	return json.Unmarshal(src, &v.value)
}


