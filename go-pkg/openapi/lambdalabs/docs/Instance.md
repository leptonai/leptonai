# Instance

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Id** | **string** | Unique identifier (ID) of an instance | 
**Name** | Pointer to **NullableString** | User-provided name for the instance | [optional] 
**Ip** | Pointer to **NullableString** | IPv4 address of the instance | [optional] 
**Status** | **string** | The current status of the instance | 
**SshKeyNames** | **[]string** | Names of the SSH keys allowed to access the instance | 
**FileSystemNames** | **[]string** | Names of the file systems, if any, attached to the instance | 
**Region** | Pointer to [**Region**](Region.md) |  | [optional] 
**InstanceType** | Pointer to [**InstanceType**](InstanceType.md) |  | [optional] 
**Hostname** | Pointer to **NullableString** | Hostname assigned to this instance, which resolves to the instance&#39;s IP. | [optional] 
**JupyterToken** | Pointer to **NullableString** | Secret token used to log into the jupyter lab server hosted on the instance. | [optional] 
**JupyterUrl** | Pointer to **NullableString** | URL that opens a jupyter lab notebook on the instance. | [optional] 

## Methods

### NewInstance

`func NewInstance(id string, status string, sshKeyNames []string, fileSystemNames []string, ) *Instance`

NewInstance instantiates a new Instance object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewInstanceWithDefaults

`func NewInstanceWithDefaults() *Instance`

NewInstanceWithDefaults instantiates a new Instance object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetId

`func (o *Instance) GetId() string`

GetId returns the Id field if non-nil, zero value otherwise.

### GetIdOk

`func (o *Instance) GetIdOk() (*string, bool)`

GetIdOk returns a tuple with the Id field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetId

`func (o *Instance) SetId(v string)`

SetId sets Id field to given value.


### GetName

`func (o *Instance) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *Instance) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *Instance) SetName(v string)`

SetName sets Name field to given value.

### HasName

`func (o *Instance) HasName() bool`

HasName returns a boolean if a field has been set.

### SetNameNil

`func (o *Instance) SetNameNil(b bool)`

 SetNameNil sets the value for Name to be an explicit nil

### UnsetName
`func (o *Instance) UnsetName()`

UnsetName ensures that no value is present for Name, not even an explicit nil
### GetIp

`func (o *Instance) GetIp() string`

GetIp returns the Ip field if non-nil, zero value otherwise.

### GetIpOk

`func (o *Instance) GetIpOk() (*string, bool)`

GetIpOk returns a tuple with the Ip field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetIp

`func (o *Instance) SetIp(v string)`

SetIp sets Ip field to given value.

### HasIp

`func (o *Instance) HasIp() bool`

HasIp returns a boolean if a field has been set.

### SetIpNil

`func (o *Instance) SetIpNil(b bool)`

 SetIpNil sets the value for Ip to be an explicit nil

### UnsetIp
`func (o *Instance) UnsetIp()`

UnsetIp ensures that no value is present for Ip, not even an explicit nil
### GetStatus

`func (o *Instance) GetStatus() string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *Instance) GetStatusOk() (*string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *Instance) SetStatus(v string)`

SetStatus sets Status field to given value.


### GetSshKeyNames

`func (o *Instance) GetSshKeyNames() []string`

GetSshKeyNames returns the SshKeyNames field if non-nil, zero value otherwise.

### GetSshKeyNamesOk

`func (o *Instance) GetSshKeyNamesOk() (*[]string, bool)`

GetSshKeyNamesOk returns a tuple with the SshKeyNames field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSshKeyNames

`func (o *Instance) SetSshKeyNames(v []string)`

SetSshKeyNames sets SshKeyNames field to given value.


### GetFileSystemNames

`func (o *Instance) GetFileSystemNames() []string`

GetFileSystemNames returns the FileSystemNames field if non-nil, zero value otherwise.

### GetFileSystemNamesOk

`func (o *Instance) GetFileSystemNamesOk() (*[]string, bool)`

GetFileSystemNamesOk returns a tuple with the FileSystemNames field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFileSystemNames

`func (o *Instance) SetFileSystemNames(v []string)`

SetFileSystemNames sets FileSystemNames field to given value.


### GetRegion

`func (o *Instance) GetRegion() Region`

GetRegion returns the Region field if non-nil, zero value otherwise.

### GetRegionOk

`func (o *Instance) GetRegionOk() (*Region, bool)`

GetRegionOk returns a tuple with the Region field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRegion

`func (o *Instance) SetRegion(v Region)`

SetRegion sets Region field to given value.

### HasRegion

`func (o *Instance) HasRegion() bool`

HasRegion returns a boolean if a field has been set.

### GetInstanceType

`func (o *Instance) GetInstanceType() InstanceType`

GetInstanceType returns the InstanceType field if non-nil, zero value otherwise.

### GetInstanceTypeOk

`func (o *Instance) GetInstanceTypeOk() (*InstanceType, bool)`

GetInstanceTypeOk returns a tuple with the InstanceType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetInstanceType

`func (o *Instance) SetInstanceType(v InstanceType)`

SetInstanceType sets InstanceType field to given value.

### HasInstanceType

`func (o *Instance) HasInstanceType() bool`

HasInstanceType returns a boolean if a field has been set.

### GetHostname

`func (o *Instance) GetHostname() string`

GetHostname returns the Hostname field if non-nil, zero value otherwise.

### GetHostnameOk

`func (o *Instance) GetHostnameOk() (*string, bool)`

GetHostnameOk returns a tuple with the Hostname field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetHostname

`func (o *Instance) SetHostname(v string)`

SetHostname sets Hostname field to given value.

### HasHostname

`func (o *Instance) HasHostname() bool`

HasHostname returns a boolean if a field has been set.

### SetHostnameNil

`func (o *Instance) SetHostnameNil(b bool)`

 SetHostnameNil sets the value for Hostname to be an explicit nil

### UnsetHostname
`func (o *Instance) UnsetHostname()`

UnsetHostname ensures that no value is present for Hostname, not even an explicit nil
### GetJupyterToken

`func (o *Instance) GetJupyterToken() string`

GetJupyterToken returns the JupyterToken field if non-nil, zero value otherwise.

### GetJupyterTokenOk

`func (o *Instance) GetJupyterTokenOk() (*string, bool)`

GetJupyterTokenOk returns a tuple with the JupyterToken field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetJupyterToken

`func (o *Instance) SetJupyterToken(v string)`

SetJupyterToken sets JupyterToken field to given value.

### HasJupyterToken

`func (o *Instance) HasJupyterToken() bool`

HasJupyterToken returns a boolean if a field has been set.

### SetJupyterTokenNil

`func (o *Instance) SetJupyterTokenNil(b bool)`

 SetJupyterTokenNil sets the value for JupyterToken to be an explicit nil

### UnsetJupyterToken
`func (o *Instance) UnsetJupyterToken()`

UnsetJupyterToken ensures that no value is present for JupyterToken, not even an explicit nil
### GetJupyterUrl

`func (o *Instance) GetJupyterUrl() string`

GetJupyterUrl returns the JupyterUrl field if non-nil, zero value otherwise.

### GetJupyterUrlOk

`func (o *Instance) GetJupyterUrlOk() (*string, bool)`

GetJupyterUrlOk returns a tuple with the JupyterUrl field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetJupyterUrl

`func (o *Instance) SetJupyterUrl(v string)`

SetJupyterUrl sets JupyterUrl field to given value.

### HasJupyterUrl

`func (o *Instance) HasJupyterUrl() bool`

HasJupyterUrl returns a boolean if a field has been set.

### SetJupyterUrlNil

`func (o *Instance) SetJupyterUrlNil(b bool)`

 SetJupyterUrlNil sets the value for JupyterUrl to be an explicit nil

### UnsetJupyterUrl
`func (o *Instance) UnsetJupyterUrl()`

UnsetJupyterUrl ensures that no value is present for JupyterUrl, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


