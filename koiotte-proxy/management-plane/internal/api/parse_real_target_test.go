package api

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestParseRealTarget_URLHttps(t *testing.T) {
	scheme, host, port, base, err := parseRealTarget(svcInput{RealURL: "https://api.real.com/v1/"})
	require.NoError(t, err)
	require.Equal(t, "https", scheme)
	require.Equal(t, "api.real.com", host)
	require.Equal(t, 443, port)
	require.Equal(t, "/v1/", base)
}

func TestParseRealTarget_URLHttpDefaultPort(t *testing.T) {
	scheme, host, port, base, err := parseRealTarget(svcInput{RealURL: "http://httpbin/anything/"})
	require.NoError(t, err)
	require.Equal(t, "http", scheme)
	require.Equal(t, "httpbin", host)
	require.Equal(t, 80, port)
	require.Equal(t, "/anything/", base)
}

func TestParseRealTarget_URLExplicitPort(t *testing.T) {
	_, host, port, _, err := parseRealTarget(svcInput{RealURL: "https://api.real.com:8443/x"})
	require.NoError(t, err)
	require.Equal(t, "api.real.com", host)
	require.Equal(t, 8443, port)
}

func TestParseRealTarget_LegacyFieldsAreHttp(t *testing.T) {
	scheme, host, port, base, err := parseRealTarget(svcInput{RealHost: "httpbin", RealPort: 80})
	require.NoError(t, err)
	require.Equal(t, "http", scheme)
	require.Equal(t, "httpbin", host)
	require.Equal(t, 80, port)
	require.Equal(t, "/", base)
}

func TestParseRealTarget_InvalidURL(t *testing.T) {
	_, _, _, _, err := parseRealTarget(svcInput{RealURL: "://nohost"})
	require.Error(t, err)
}
