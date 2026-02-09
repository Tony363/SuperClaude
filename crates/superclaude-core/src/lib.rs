//! Shared types, config parsers, and inventory scanning for SuperClaude.

#[cfg(feature = "glob")]
pub mod config;
#[cfg(feature = "glob")]
pub mod inventory;
#[cfg(feature = "glob")]
pub mod metrics_reader;

pub mod types;

pub use types::*;
