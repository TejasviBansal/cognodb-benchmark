import ssl
import socket
from cryptography import x509
from cryptography.hazmat.backends import default_backend

hostname = "2961ad1d.databases.neo4j.io"
port = 7687

ctx = ssl._create_unverified_context()
with socket.create_connection((hostname, port)) as sock:
    with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
        der_cert = ssock.getpeercert(binary_form=True)
        cert = x509.load_der_x509_certificate(der_cert, default_backend())
        print("Issuer: ", cert.issuer)
        print("Subject:", cert.subject)
        print("Valid from:", cert.not_valid_before_utc)
        print("Valid until:", cert.not_valid_after_utc)