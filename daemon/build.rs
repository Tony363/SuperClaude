use std::path::PathBuf;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let proto_path = PathBuf::from("proto/superclaude.proto");

    println!("cargo:rerun-if-changed={}", proto_path.display());

    if !proto_path.exists() {
        eprintln!(
            "Warning: {} not found. Copy from Zed crate or SuperClaude repo.",
            proto_path.display()
        );
        return Ok(());
    }

    // Compile proto to OUT_DIR (standard tonic location)
    tonic_build::configure()
        .build_server(true)
        .build_client(false)
        .compile_protos(&[&proto_path], &["proto/"])?;

    Ok(())
}
