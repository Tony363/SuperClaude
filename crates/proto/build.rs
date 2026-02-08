use std::path::PathBuf;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let proto_path = PathBuf::from("proto/superclaude.proto");

    println!("cargo:rerun-if-changed={}", proto_path.display());

    if !proto_path.exists() {
        eprintln!(
            "Error: {} not found. Proto file must exist at build time.",
            proto_path.display()
        );
        return Err("Proto file not found".into());
    }

    // Compile proto with both server and client support
    // Server needed for daemon, client needed for dashboard/Tauri backend
    tonic_build::configure()
        .build_server(true)
        .build_client(true)
        .compile_protos(&[&proto_path], &["proto/"])?;

    Ok(())
}
