# FileSystem

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Id** | **string** | Unique identifier (ID) of a file system | 
**Name** | **string** | Name of a file system | 
**Created** | **string** | A date and time, formatted as an ISO 8601 time stamp | 
**CreatedBy** | [**User**](User.md) |  | 
**MountPoint** | **string** | Absolute path indicating where on instances the file system will be mounted | 
**Region** | [**Region**](Region.md) |  | 
**IsInUse** | **bool** | Whether the file system is currently in use by an instance. File systems that are in use cannot be deleted. | 

## Methods

### NewFileSystem

`func NewFileSystem(id string, name string, created string, createdBy User, mountPoint string, region Region, isInUse bool, ) *FileSystem`

NewFileSystem instantiates a new FileSystem object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewFileSystemWithDefaults

`func NewFileSystemWithDefaults() *FileSystem`

NewFileSystemWithDefaults instantiates a new FileSystem object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetId

`func (o *FileSystem) GetId() string`

GetId returns the Id field if non-nil, zero value otherwise.

### GetIdOk

`func (o *FileSystem) GetIdOk() (*string, bool)`

GetIdOk returns a tuple with the Id field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetId

`func (o *FileSystem) SetId(v string)`

SetId sets Id field to given value.


### GetName

`func (o *FileSystem) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *FileSystem) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *FileSystem) SetName(v string)`

SetName sets Name field to given value.


### GetCreated

`func (o *FileSystem) GetCreated() string`

GetCreated returns the Created field if non-nil, zero value otherwise.

### GetCreatedOk

`func (o *FileSystem) GetCreatedOk() (*string, bool)`

GetCreatedOk returns a tuple with the Created field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCreated

`func (o *FileSystem) SetCreated(v string)`

SetCreated sets Created field to given value.


### GetCreatedBy

`func (o *FileSystem) GetCreatedBy() User`

GetCreatedBy returns the CreatedBy field if non-nil, zero value otherwise.

### GetCreatedByOk

`func (o *FileSystem) GetCreatedByOk() (*User, bool)`

GetCreatedByOk returns a tuple with the CreatedBy field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCreatedBy

`func (o *FileSystem) SetCreatedBy(v User)`

SetCreatedBy sets CreatedBy field to given value.


### GetMountPoint

`func (o *FileSystem) GetMountPoint() string`

GetMountPoint returns the MountPoint field if non-nil, zero value otherwise.

### GetMountPointOk

`func (o *FileSystem) GetMountPointOk() (*string, bool)`

GetMountPointOk returns a tuple with the MountPoint field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMountPoint

`func (o *FileSystem) SetMountPoint(v string)`

SetMountPoint sets MountPoint field to given value.


### GetRegion

`func (o *FileSystem) GetRegion() Region`

GetRegion returns the Region field if non-nil, zero value otherwise.

### GetRegionOk

`func (o *FileSystem) GetRegionOk() (*Region, bool)`

GetRegionOk returns a tuple with the Region field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRegion

`func (o *FileSystem) SetRegion(v Region)`

SetRegion sets Region field to given value.


### GetIsInUse

`func (o *FileSystem) GetIsInUse() bool`

GetIsInUse returns the IsInUse field if non-nil, zero value otherwise.

### GetIsInUseOk

`func (o *FileSystem) GetIsInUseOk() (*bool, bool)`

GetIsInUseOk returns a tuple with the IsInUse field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetIsInUse

`func (o *FileSystem) SetIsInUse(v bool)`

SetIsInUse sets IsInUse field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


