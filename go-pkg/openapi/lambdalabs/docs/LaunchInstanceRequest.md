# LaunchInstanceRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**RegionName** | **string** | Short name of a region | 
**InstanceTypeName** | **string** | Name of an instance type | 
**SshKeyNames** | **[]string** | Names of the SSH keys to allow access to the instances. Currently, exactly one SSH key must be specified. | 
**FileSystemNames** | Pointer to **[]string** | Names of the file systems to attach to the instances. Currently, only one (if any) file system may be specified. | [optional] 
**Quantity** | Pointer to **int32** | Number of instances to launch | [optional] [default to 1]
**Name** | Pointer to **NullableString** | User-provided name for the instance | [optional] 

## Methods

### NewLaunchInstanceRequest

`func NewLaunchInstanceRequest(regionName string, instanceTypeName string, sshKeyNames []string, ) *LaunchInstanceRequest`

NewLaunchInstanceRequest instantiates a new LaunchInstanceRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewLaunchInstanceRequestWithDefaults

`func NewLaunchInstanceRequestWithDefaults() *LaunchInstanceRequest`

NewLaunchInstanceRequestWithDefaults instantiates a new LaunchInstanceRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetRegionName

`func (o *LaunchInstanceRequest) GetRegionName() string`

GetRegionName returns the RegionName field if non-nil, zero value otherwise.

### GetRegionNameOk

`func (o *LaunchInstanceRequest) GetRegionNameOk() (*string, bool)`

GetRegionNameOk returns a tuple with the RegionName field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRegionName

`func (o *LaunchInstanceRequest) SetRegionName(v string)`

SetRegionName sets RegionName field to given value.


### GetInstanceTypeName

`func (o *LaunchInstanceRequest) GetInstanceTypeName() string`

GetInstanceTypeName returns the InstanceTypeName field if non-nil, zero value otherwise.

### GetInstanceTypeNameOk

`func (o *LaunchInstanceRequest) GetInstanceTypeNameOk() (*string, bool)`

GetInstanceTypeNameOk returns a tuple with the InstanceTypeName field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetInstanceTypeName

`func (o *LaunchInstanceRequest) SetInstanceTypeName(v string)`

SetInstanceTypeName sets InstanceTypeName field to given value.


### GetSshKeyNames

`func (o *LaunchInstanceRequest) GetSshKeyNames() []string`

GetSshKeyNames returns the SshKeyNames field if non-nil, zero value otherwise.

### GetSshKeyNamesOk

`func (o *LaunchInstanceRequest) GetSshKeyNamesOk() (*[]string, bool)`

GetSshKeyNamesOk returns a tuple with the SshKeyNames field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSshKeyNames

`func (o *LaunchInstanceRequest) SetSshKeyNames(v []string)`

SetSshKeyNames sets SshKeyNames field to given value.


### GetFileSystemNames

`func (o *LaunchInstanceRequest) GetFileSystemNames() []string`

GetFileSystemNames returns the FileSystemNames field if non-nil, zero value otherwise.

### GetFileSystemNamesOk

`func (o *LaunchInstanceRequest) GetFileSystemNamesOk() (*[]string, bool)`

GetFileSystemNamesOk returns a tuple with the FileSystemNames field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFileSystemNames

`func (o *LaunchInstanceRequest) SetFileSystemNames(v []string)`

SetFileSystemNames sets FileSystemNames field to given value.

### HasFileSystemNames

`func (o *LaunchInstanceRequest) HasFileSystemNames() bool`

HasFileSystemNames returns a boolean if a field has been set.

### GetQuantity

`func (o *LaunchInstanceRequest) GetQuantity() int32`

GetQuantity returns the Quantity field if non-nil, zero value otherwise.

### GetQuantityOk

`func (o *LaunchInstanceRequest) GetQuantityOk() (*int32, bool)`

GetQuantityOk returns a tuple with the Quantity field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetQuantity

`func (o *LaunchInstanceRequest) SetQuantity(v int32)`

SetQuantity sets Quantity field to given value.

### HasQuantity

`func (o *LaunchInstanceRequest) HasQuantity() bool`

HasQuantity returns a boolean if a field has been set.

### GetName

`func (o *LaunchInstanceRequest) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *LaunchInstanceRequest) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *LaunchInstanceRequest) SetName(v string)`

SetName sets Name field to given value.

### HasName

`func (o *LaunchInstanceRequest) HasName() bool`

HasName returns a boolean if a field has been set.

### SetNameNil

`func (o *LaunchInstanceRequest) SetNameNil(b bool)`

 SetNameNil sets the value for Name to be an explicit nil

### UnsetName
`func (o *LaunchInstanceRequest) UnsetName()`

UnsetName ensures that no value is present for Name, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


