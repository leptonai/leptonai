package httpapi

// https://docs.aws.amazon.com/step-functions/latest/apireference/CommonErrors.html
const (
	ErrorCodeInternalFailure             = "InternalFailure"
	ErrorCodeInvalidParameterCombination = "InvalidParameterCombination"
	ErrorCodeInvalidParameterValue       = "InvalidParameterValue"
	ErrorCodeInvalidQueryParameter       = "InvalidQueryParameter"
	ErrorCodeMissingParameter            = "MissingParameter"
	ErrorCodeValidationError             = "ValidationError"
)
