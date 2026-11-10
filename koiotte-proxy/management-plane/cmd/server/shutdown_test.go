package main

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

type fakeStopper struct {
	release chan struct{}
	stopped bool
}

func (f *fakeStopper) GracefulStop() { <-f.release }

func (f *fakeStopper) Stop() {
	f.stopped = true
	close(f.release)
}

func TestStopGracefully_ForcesStopWhenStreamsNeverEnd(t *testing.T) {
	f := &fakeStopper{release: make(chan struct{})}
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Millisecond)
	defer cancel()

	require.False(t, stopGracefully(ctx, f))
	require.True(t, f.stopped)
}

func TestStopGracefully_ReturnsWhenStreamsDrain(t *testing.T) {
	f := &fakeStopper{release: make(chan struct{})}
	close(f.release)

	require.True(t, stopGracefully(context.Background(), f))
	require.False(t, f.stopped)
}
