package exitcode

import "fmt"

// CodeToError converts exit code to error message
// https://tldp.org/LDP/abs/html/exitcodes.html
func CodeToError(exitCode int32) string {
	switch exitCode {
	case 0:
		return "Success"
	case 1:
		return "General application errors: such as divide by zero and other impermissible operations"
	case 2:
		return "Misuse of shell builtins: missing keyword or command"
	case 126:
		return "Command invoked cannot execute: permission problem or command is not an executable"
	case 127:
		return "Command not found: possible problem with $PATH or a typo"
	case 130: // 128 + 2
		return "Terminated by SIGINT (Control-C): SIGNIT (Control-C) is fatal error signal 2"
	case 137: // 128 + 9
		return "Terminated by SIGKILL: SIGKILL is fatal error signal 9. Possibly OOM killer"
	case 139: // 128 + 11
		return "Terminated by SIGSEGV: SIGSEGV is fatal error signal 11"
	case 143: // 128 + 15
		return "Terminated by SIGTERM: SIGTERM is fatal error signal 15"
	default:
		if exitCode >= 128 && exitCode <= 165 {
			signal := exitCode - 128
			return fmt.Sprintf("Fatal error signal %d: Terminated by signal %d", signal, signal)
		}
		return fmt.Sprintf("Unknown error with exit code %d", exitCode)
	}
}
