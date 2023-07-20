# ErrorResponseBody

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Error** | [**ModelError**](ModelError.md) |  | 
**FieldErrors** | Pointer to [**map[string]ModelError**](ModelError.md) | Details about errors on a per-parameter basis | [optional] 

## Methods

### NewErrorResponseBody

`func NewErrorResponseBody(error_ ModelError, ) *ErrorResponseBody`

NewErrorResponseBody instantiates a new ErrorResponseBody object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewErrorResponseBodyWithDefaults

`func NewErrorResponseBodyWithDefaults() *ErrorResponseBody`

NewErrorResponseBodyWithDefaults instantiates a new ErrorResponseBody object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetError

`func (o *ErrorResponseBody) GetError() ModelError`

GetError returns the Error field if non-nil, zero value otherwise.

### GetErrorOk

`func (o *ErrorResponseBody) GetErrorOk() (*ModelError, bool)`

GetErrorOk returns a tuple with the Error field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetError

`func (o *ErrorResponseBody) SetError(v ModelError)`

SetError sets Error field to given value.


### GetFieldErrors

`func (o *ErrorResponseBody) GetFieldErrors() map[string]ModelError`

GetFieldErrors returns the FieldErrors field if non-nil, zero value otherwise.

### GetFieldErrorsOk

`func (o *ErrorResponseBody) GetFieldErrorsOk() (*map[string]ModelError, bool)`

GetFieldErrorsOk returns a tuple with the FieldErrors field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFieldErrors

`func (o *ErrorResponseBody) SetFieldErrors(v map[string]ModelError)`

SetFieldErrors sets FieldErrors field to given value.

### HasFieldErrors

`func (o *ErrorResponseBody) HasFieldErrors() bool`

HasFieldErrors returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


