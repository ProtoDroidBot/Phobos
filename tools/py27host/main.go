// py27host starts the client-supplied Python 2.7 DLL as a separate process.
//
// The DLL path is supplied through PHOBOS_PYTHON27_DLL. Remaining command-line
// arguments are passed directly to Python's Py_Main, making the host behave
// like a minimal python.exe without embedding Python 2 in the Phobos process.
package main

import (
	"fmt"
	"os"
	"syscall"
	"unsafe"
)

func main() {
	dllPath := os.Getenv("PHOBOS_PYTHON27_DLL")
	if dllPath == "" {
		fmt.Fprintln(os.Stderr, "PHOBOS_PYTHON27_DLL is not set")
		os.Exit(2)
	}
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: py27host.exe SCRIPT.py [args...]")
		os.Exit(2)
	}

	dll := syscall.NewLazyDLL(dllPath)
	pyMain := dll.NewProc("Py_Main")
	if err := dll.Load(); err != nil {
		fmt.Fprintf(os.Stderr, "unable to load %s: %v\n", dllPath, err)
		os.Exit(3)
	}
	if err := pyMain.Find(); err != nil {
		fmt.Fprintf(os.Stderr, "Py_Main is unavailable in %s: %v\n", dllPath, err)
		os.Exit(3)
	}

	args := append([]string{"python.exe"}, os.Args[1:]...)
	argv := make([]*byte, len(args))
	for index, arg := range args {
		pointer, err := syscall.BytePtrFromString(arg)
		if err != nil {
			fmt.Fprintf(os.Stderr, "invalid argument %q: %v\n", arg, err)
			os.Exit(2)
		}
		argv[index] = pointer
	}

	result, _, callErr := pyMain.Call(
		uintptr(len(argv)),
		uintptr(unsafe.Pointer(&argv[0])),
	)
	if callErr != syscall.Errno(0) {
		fmt.Fprintf(os.Stderr, "Py_Main failed: %v\n", callErr)
	}
	os.Exit(int(result))
}
