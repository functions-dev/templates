package function

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// TestHandle verifies that the blog is built and served correctly.
// Requires 'make' to be run first to generate the dist/ directory.
func TestHandle(t *testing.T) {
	var (
		f   = New()
		w   = httptest.NewRecorder()
		req = httptest.NewRequest("GET", "http://example.com/", nil)
		res *http.Response
	)
	f.Handle(w, req)
	res = w.Result()
	defer res.Body.Close()

	if res.StatusCode != 200 {
		t.Fatalf("unexpected response code: %v", res.StatusCode)
	}

	body := w.Body.String()
	if !strings.Contains(body, "Functions Go Blog") {
		t.Fatalf("response body does not contain blog title, got: %s", body[:200])
	}
}
