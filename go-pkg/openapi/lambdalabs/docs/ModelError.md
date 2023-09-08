# ModelError

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Code** | [**ErrorCode**](ErrorCode.md) |  | 
**Message** | **string** | Detailed description of the error | 
**Suggestion** | Pointer to **NullableString** | Suggestion of possible ways to fix the error. | [optional] 

## Methods

### NewModelError

`func NewModelError(code ErrorCode, message string, ) *ModelError`

NewModelError instantiates a new ModelError object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewModelErrorWithDefaults

`func NewModelErrorWithDefaults() *ModelError`

NewModelErrorWithDefaults instantiates a new ModelError object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetCode

`func (o *ModelError) GetCode() ErrorCode`

GetCode returns the Code field if non-nil, zero value otherwise.

### GetCodeOk

`func (o *ModelError) GetCodeOk() (*ErrorCode, bool)`

GetCodeOk returns a tuple with the Code field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCode

`func (o *ModelError) SetCode(v ErrorCode)`

SetCode sets Code field to given value.


### GetMessage

`func (o *ModelError) GetMessage() string`

GetMessage returns the Message field if non-nil, zero value otherwise.

### GetMessageOk

`func (o *ModelError) GetMessageOk() (*string, bool)`

GetMessageOk returns a tuple with the Message field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMessage

`func (o *ModelError) SetMessage(v string)`

SetMessage sets Message field to given value.


### GetSuggestion

`func (o *ModelError) GetSuggestion() string`

GetSuggestion returns the Suggestion field if non-nil, zero value otherwise.

### GetSuggestionOk

`func (o *ModelError) GetSuggestionOk() (*string, bool)`

GetSuggestionOk returns a tuple with the Suggestion field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSuggestion

`func (o *ModelError) SetSuggestion(v string)`

SetSuggestion sets Suggestion field to given value.

### HasSuggestion

`func (o *ModelError) HasSuggestion() bool`

HasSuggestion returns a boolean if a field has been set.

### SetSuggestionNil

`func (o *ModelError) SetSuggestionNil(b bool)`

 SetSuggestionNil sets the value for Suggestion to be an explicit nil

### UnsetSuggestion
`func (o *ModelError) UnsetSuggestion()`

UnsetSuggestion ensures that no value is present for Suggestion, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


