import os
import subprocess
import shutil

def check_openssl():
    """Check if OpenSSL is available in the system."""
    if not shutil.which('openssl'):
        print("Error: OpenSSL is not installed or not available in system PATH")
        print("Please install OpenSSL and try again")
        return False
    return True

def create_root_ca():
    print("Creating root CA certificate...")
    
    # Generate root key with password protection
    subprocess.run([
        "openssl", "genrsa", "-des3", "-passout", "pass:1234",
        "-out", "LocalRootCA.key", "4096"
    ])
    
    # Generate root certificate
    subprocess.run([
        "openssl", "req", "-x509", "-new", "-nodes",
        "-key", "LocalRootCA.key", "-sha256", "-days", "3650",
        "-passin", "pass:1234",
        "-out", "LocalRootCA.crt",
        "-subj", "/C=US/ST=State/L=City/O=Local CA/OU=Development/CN=Local Root CA"
    ])

    # Convert crt to pem
    subprocess.run([
        "openssl", "x509", "-in", "LocalRootCA.crt",
        "-out", "LocalRootCA.pem", "-outform", "PEM"
    ])
    
    print("\nRoot CA created successfully!")
    print("Location: ./LocalRootCA.key, ./LocalRootCA.crt and ./LocalRootCA.pem")
    print("Root CA Key Password: 1234")

def create_key(domain):
    key_file = f"domains/{domain}/{domain}.key"
    subprocess.run(["openssl", "genrsa", "-out", key_file, "2048"])
    print(f"Generated key: {key_file}")
    return key_file

def create_csr(domain, config_file):
    csr_file = f"domains/{domain}/{domain}.csr"
    subprocess.run([
        "openssl", "req", "-new", "-key", f"domains/{domain}/{domain}.key",
        "-out", csr_file, "-config", config_file
    ])
    print(f"Generated CSR: {csr_file}")
    return csr_file

def sign_certificate(domain, config_file):
    crt_file = f"domains/{domain}/{domain}.crt"
    subprocess.run([
        "openssl", "x509", "-req", "-in", f"domains/{domain}/{domain}.csr",
        "-CA", "LocalRootCA.crt", "-CAkey", "LocalRootCA.key",
        "-passin", "pass:1234",
        "-CAcreateserial", "-out", crt_file, "-days", "365",
        "-sha256", "-extfile", config_file, "-extensions", "v3_req"
    ])
    print(f"Generated Certificate: {crt_file}")
    return crt_file

def create_openssl_config(domain, alt_names):
    # Remove wildcard for directory name if present
    dir_domain = domain.replace('*.', '')
    config_file = f"domains/{dir_domain}/openssl.cnf"
    with open(config_file, 'w') as f:
        f.write(f"""
[ req ]
default_bits       = 2048
distinguished_name = req_distinguished_name
req_extensions     = req_ext
x509_extensions    = v3_req
prompt             = no

[ req_distinguished_name ]
C  = US
ST = State
L  = City
O  = Organization
OU = Organizational Unit
CN = {domain}

[ req_ext ]
subjectAltName = @alt_names

[ v3_req ]
subjectAltName = @alt_names

[ alt_names ]
""")
        for i, alt_name in enumerate(alt_names, start=1):
            f.write(f"DNS.{i} = {alt_name}\n")
    print(f"Generated OpenSSL config: {config_file}")
    return config_file

def main():
    # Check if OpenSSL is available
    if not check_openssl():
        return

    print("""
Certificate Generator with Wildcard Support
-----------------------------------------
For wildcard certificates, use the following format:
- Main domain: example.com
- To include wildcard: *.example.com
Example alternate names: 
- *.subdomain.example.com
- specific.example.com
""")

    # Check if root CA exists
    if not (os.path.exists("LocalRootCA.key") and os.path.exists("LocalRootCA.crt") and os.path.exists("LocalRootCA.pem")):
        response = input("Root CA certificate not found. Do you want to create it? (y/n): ").strip().lower()
        if response == 'y':
            create_root_ca(prefixName="Local")
        else:
            print("Cannot proceed without root CA certificate.")
            return

    domain = input("Enter the main domain (e.g., example.com or *.example.com): ").strip()

    if not domain:
        print("Domain cannot be empty!")
        return

    print("\nEnter alternate domain names (comma-separated)")
    print("Examples:")
    print("- For wildcard subdomains: *.app.example.com")
    print("- For specific domains: admin.example.com")
    alt_names = input("Alternate names: ").strip()
    
    # Add the main domain to alt_names if it's not already included
    alt_names_list = [name.strip() for name in alt_names.split(',') if name.strip()]
    if domain not in alt_names_list:
        alt_names_list.insert(0, domain)

    # Create domains directory if it doesn't exist
    if not os.path.exists("domains"):
        os.makedirs("domains")
        print("Created directory: domains")

    # Create directory for the new domain
    # Remove wildcard for directory name if present
    dir_domain = domain.replace('*.', '')
    domain_dir = f"domains/{dir_domain}"
    if not os.path.exists(domain_dir):
        os.makedirs(domain_dir)
        print(f"Created directory: {domain_dir}")

    # Generate openssl.cnf with custom configurations
    config_file = create_openssl_config(domain, alt_names_list)

    # Generate key, CSR, and signed certificate
    create_key(dir_domain)
    create_csr(dir_domain, config_file)
    sign_certificate(dir_domain, config_file)

    print("\nCertificate generation complete!")
    print("\nUsage Instructions:")
    print("1. Your certificate files are in the 'domains' directory")
    if '*' in domain:
        print("2. This wildcard certificate will work for all subdomains at the specified level")
        print(f"   For example, if your domain is *.example.com, it will work for:")
        print("   - test.example.com")
        print("   - dev.example.com")
        print("   But NOT for: sub.test.example.com (different level)")

if __name__ == "__main__":
    main()
