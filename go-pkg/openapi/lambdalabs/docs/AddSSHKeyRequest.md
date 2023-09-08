# AddSSHKeyRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Name** | **string** | Name of the SSH key | 
**PublicKey** | Pointer to **string** | Public key for the SSH key | [optional] 

## Methods

### NewAddSSHKeyRequest

`func NewAddSSHKeyRequest(name string, ) *AddSSHKeyRequest`

NewAddSSHKeyRequest instantiates a new AddSSHKeyRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewAddSSHKeyRequestWithDefaults

`func NewAddSSHKeyRequestWithDefaults() *AddSSHKeyRequest`

NewAddSSHKeyRequestWithDefaults instantiates a new AddSSHKeyRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetName

`func (o *AddSSHKeyRequest) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *AddSSHKeyRequest) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *AddSSHKeyRequest) SetName(v string)`

SetName sets Name field to given value.


### GetPublicKey

`func (o *AddSSHKeyRequest) GetPublicKey() string`

GetPublicKey returns the PublicKey field if non-nil, zero value otherwise.

### GetPublicKeyOk

`func (o *AddSSHKeyRequest) GetPublicKeyOk() (*string, bool)`

GetPublicKeyOk returns a tuple with the PublicKey field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPublicKey

`func (o *AddSSHKeyRequest) SetPublicKey(v string)`

SetPublicKey sets PublicKey field to given value.

### HasPublicKey

`func (o *AddSSHKeyRequest) HasPublicKey() bool`

HasPublicKey returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


