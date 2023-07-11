## Best Practices

### Logging

1. Use Zap as the default logging library.

2. Always write logs to stdout.

3. Be clear and explicit about the context of the logging message.

4. Use the debugging and info levels for informational logging. When in doubt, always log. Log at the beginning and end of an operation.

5. Do not log within a tight for loop. However, do log when retrying on errors with backoff.

6. Use the warning level for expected errors. Log close to the expected error since the operation would normally continue.

7. Use the error level for unexpected errors. Do not log the error if it is returned. Always let the caller log the error.

8. Only use the fatal level for unrecoverable errors.