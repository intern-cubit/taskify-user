"""
Quick diagnostic script to check system readiness for Vahan automation
Run this script if you're experiencing connection issues
"""

import subprocess
import socket
import sys
import platform

def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def check_internet():
    """Check basic internet connectivity"""
    print_header("1. Internet Connectivity Check")
    
    try:
        # Try to resolve Google DNS
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        print("✅ Internet connection: OK")
        return True
    except OSError:
        print("❌ Internet connection: FAILED")
        print("   → Check your network connection")
        return False

def check_vahan_connectivity():
    """Check if Vahan website is accessible"""
    print_header("2. Vahan Website Connectivity")
    
    hostname = "vahan.parivahan.gov.in"
    
    # DNS Resolution
    try:
        ip = socket.gethostbyname(hostname)
        print(f"✅ DNS Resolution: OK ({hostname} → {ip})")
    except socket.gaierror:
        print(f"❌ DNS Resolution: FAILED")
        print(f"   → Cannot resolve {hostname}")
        return False
    
    # Port 443 (HTTPS) connectivity
    try:
        sock = socket.create_connection((hostname, 443), timeout=10)
        sock.close()
        print(f"✅ HTTPS Connection: OK (Port 443 accessible)")
        return True
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        print(f"❌ HTTPS Connection: FAILED")
        print(f"   → Error: {type(e).__name__}")
        print(f"   → Possible firewall/proxy blocking")
        return False

def check_chrome():
    """Check Chrome installation"""
    print_header("3. Chrome Browser Check")
    
    try:
        if platform.system() == "Windows":
            # Check Chrome version
            result = subprocess.run(
                ['powershell', '-Command', 
                 '(Get-Item "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe").VersionInfo.ProductVersion'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                version = result.stdout.strip()
                print(f"✅ Chrome Browser: Installed (Version {version})")
                return True
            else:
                print("⚠️  Chrome Browser: Not found in default location")
                return False
        else:
            print("⚠️  Chrome check: Only supported on Windows")
            return None
    except Exception as e:
        print(f"⚠️  Chrome Browser: Check failed ({str(e)})")
        return None

def check_python_packages():
    """Check required Python packages"""
    print_header("4. Python Packages Check")
    
    packages = {
        'selenium': None,
        'undetected_chromedriver': None,
        'webdriver_manager': None
    }
    
    for package in packages.keys():
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'show', package],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Extract version
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        packages[package] = line.split(':')[1].strip()
                        break
                print(f"✅ {package}: {packages[package]}")
            else:
                packages[package] = None
                print(f"❌ {package}: NOT INSTALLED")
        except Exception as e:
            print(f"⚠️  {package}: Check failed ({str(e)})")
    
    return all(v is not None for v in packages.values())

def check_firewall():
    """Check Windows Firewall status"""
    print_header("5. Windows Firewall Check")
    
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ['powershell', '-Command', 
                 'Get-NetFirewallProfile | Select-Object Name, Enabled'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                print(result.stdout)
                print("ℹ️  If firewall is enabled, try temporarily disabling it")
            else:
                print("⚠️  Could not check firewall status")
        else:
            print("ℹ️  Firewall check: Only supported on Windows")
    except Exception as e:
        print(f"⚠️  Firewall check failed: {str(e)}")

def check_proxy():
    """Check proxy settings"""
    print_header("6. Proxy Settings Check")
    
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ['powershell', '-Command', 
                 'Get-ItemProperty -Path "Registry::HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" | Select-Object ProxyEnable, ProxyServer'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                if "ProxyEnable" in result.stdout:
                    if "ProxyEnable : 1" in result.stdout:
                        print("⚠️  Proxy is ENABLED")
                        print("   → This might interfere with automation")
                        if "ProxyServer :" in result.stdout:
                            print(result.stdout)
                    else:
                        print("✅ Proxy: Disabled")
            else:
                print("⚠️  Could not check proxy settings")
        else:
            print("ℹ️  Proxy check: Only supported on Windows")
    except Exception as e:
        print(f"⚠️  Proxy check failed: {str(e)}")

def main():
    """Run all diagnostic checks"""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  VAHAN AUTOMATION - SYSTEM DIAGNOSTIC".center(58) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)
    
    results = {
        'internet': check_internet(),
        'vahan': check_vahan_connectivity(),
        'chrome': check_chrome(),
        'packages': check_python_packages()
    }
    
    check_firewall()
    check_proxy()
    
    # Summary
    print_header("DIAGNOSTIC SUMMARY")
    
    all_ok = all(v for v in results.values() if v is not None)
    
    if all_ok:
        print("\n✅ All checks PASSED!")
        print("   System appears ready for Vahan automation")
    else:
        print("\n⚠️  Some checks FAILED!")
        print("\nRecommendations:")
        
        if not results['internet']:
            print("  • Fix internet connection first")
        
        if not results['vahan']:
            print("  • Check firewall/antivirus settings")
            print("  • Try accessing https://vahan.parivahan.gov.in in browser")
            print("  • Check proxy settings")
        
        if results['chrome'] is False:
            print("  • Install/Update Google Chrome browser")
        
        if not results['packages']:
            print("  • Install missing Python packages:")
            print("    pip install selenium undetected-chromedriver webdriver-manager")
    
    print("\n" + "="*60)
    print("For detailed troubleshooting, see TROUBLESHOOTING.md")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDiagnostic interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Diagnostic error: {str(e)}")
        import traceback
        traceback.print_exc()
