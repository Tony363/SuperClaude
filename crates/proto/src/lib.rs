//! Shared protobuf types for SuperClaude gRPC services.
//!
//! Generated from `proto/superclaude.proto`. Provides both server and client stubs.

#[allow(clippy::all)]
pub mod superclaude_v1 {
    tonic::include_proto!("superclaude.v1");
}

// Re-export everything at crate root for convenience
pub use superclaude_v1::*;
