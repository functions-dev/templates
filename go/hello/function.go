package function

import (
	"fmt"
	"net/http"
)

// function provided by this library
type MyFunction struct{}

// New constructs an instance of this function
// This function must be named "New",accept no arguments and return a structure
// which exports AT LEAST a Handle method
func New() *MyFunction {
	return &MyFunction{}
}

// Handle an HTTP Request.
func (f *MyFunction) Handle(w http.ResponseWriter, r *http.Request) {
	fmt.Print("Received a request\n")      //printed on server
	fmt.Fprint(w, "Hello Go World!") //send to client
}
