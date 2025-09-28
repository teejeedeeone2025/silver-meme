#!/usr/bin/env python3
"""
Create Chrome Profile via VNC
Python script equivalent of the GitHub Actions workflow
"""

import os
import subprocess
import sys
import time
import signal
import threading

def run_command(cmd, shell=False, check=True, capture_output=False):
    """Helper function to run shell commands"""
    print(f"Running: {cmd}")
    if shell:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=capture_output)
    else:
        result = subprocess.run(cmd, check=check, capture_output=capture_output)
    return result

def install_packages():
    """Install VNC, XFCE, Chrome, and cloudflared"""
    print("=== Installing VNC, XFCE, and Chrome ===")
    
    # Update package list
    run_command(["sudo", "apt-get", "update"])
    
    # Install VNC and XFCE
    run_command(["sudo", "apt-get", "install", "-y", "tigervnc-standalone-server", "xfce4", "xfce4-goodies", "wget"])
    
    # Install Chrome
    run_command("wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb", shell=True)
    run_command("sudo dpkg -i google-chrome-stable_current_amd64.deb || sudo apt-get install -y -f", shell=True)
    run_command("rm google-chrome-stable_current_amd64.deb", shell=True)
    
    print("=== Installing cloudflared ===")
    run_command("wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb", shell=True)
    run_command("sudo dpkg -i cloudflared-linux-amd64.deb", shell=True)

def setup_vnc_password():
    """Set up VNC password"""
    print("=== Setting VNC password ===")
    
    # Create VNC directory
    vnc_dir = os.path.expanduser("~/.vnc")
    os.makedirs(vnc_dir, exist_ok=True)
    
    # Set VNC password to 'password'
    with open(f"{vnc_dir}/passwd", "w") as f:
        subprocess.run(["echo", "password"], stdout=f, check=True)
    
    # Set proper permissions
    os.chmod(f"{vnc_dir}/passwd", 0o600)

def start_vnc_server():
    """Start VNC server with XFCE"""
    print("=== Starting VNC Server with XFCE ===")
    
    # Start VNC server in background
    vnc_process = subprocess.Popen([
        "vncserver", ":1", 
        "-geometry", "1280x800", 
        "-depth", "24", 
        "-localhost", "no", 
        "-xstartup", "/usr/bin/xfce4-session"
    ])
    
    # Wait for VNC server to start
    time.sleep(5)
    
    return vnc_process

def start_cloudflared_tunnel():
    """Start Cloudflare tunnel to expose VNC port"""
    print("=== Starting Cloudflare Tunnel ===")
    
    print("=" * 50)
    print("CONNECTION INSTRUCTIONS:")
    print("1. Download cloudflared on your local machine from:")
    print("   https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe")
    print("2. Run the command below in your local command prompt.")
    print("3. Connect your VNC viewer (like TigerVNC) to 'localhost:5900'")
    print("=" * 50)
    
    # Set environment variable for cloudflared
    env = os.environ.copy()
    env["TUNNEL_ORIGIN_CERT"] = "/dev/null"
    
    # Start cloudflared tunnel
    tunnel_process = subprocess.Popen([
        "cloudflared", "tunnel", "--url", "tcp://localhost:5901"
    ], env=env)
    
    return tunnel_process

def signal_handler(signum, frame):
    """Handle cleanup on interrupt"""
    print(f"\nReceived signal {signum}. Cleaning up...")
    
    # Kill VNC server
    try:
        run_command("vncserver -kill :1", shell=True, check=False)
    except:
        pass
    
    sys.exit(0)

def main():
    """Main function to execute the workflow"""
    print("Starting Chrome Profile setup via VNC...")
    
    # Set up signal handlers for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Install required packages
        install_packages()
        
        # Set up VNC password
        setup_vnc_password()
        
        # Start VNC server
        vnc_process = start_vnc_server()
        
        # Start Cloudflare tunnel
        tunnel_process = start_cloudflared_tunnel()
        
        print("\nSetup completed successfully!")
        print("VNC server and Cloudflare tunnel are running...")
        print("Press Ctrl+C to stop the services and exit.")
        
        # Keep the script running
        try:
            while True:
                time.sleep(1)
                
                # Check if processes are still alive
                if vnc_process.poll() is not None:
                    print("VNC server process died!")
                    break
                if tunnel_process.poll() is not None:
                    print("Cloudflare tunnel process died!")
                    break
                    
        except KeyboardInterrupt:
            print("\nShutting down...")
            
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with return code {e.returncode}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        print("Cleaning up...")
        try:
            if 'vnc_process' in locals():
                vnc_process.terminate()
                run_command("vncserver -kill :1", shell=True, check=False)
        except:
            pass
        
        try:
            if 'tunnel_process' in locals():
                tunnel_process.terminate()
        except:
            pass

if __name__ == "__main__":
    main()
