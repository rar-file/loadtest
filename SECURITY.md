# Security Policy

## Supported Versions

The following versions of LoadTest are currently supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| 0.1.x   | :x:                |
| < 0.1   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability within LoadTest, please follow these steps:

### 1. Do Not Disclose Publicly

Please **DO NOT** create a public GitHub issue for security vulnerabilities.

### 2. Contact Us Directly

Send an email to security@loadtest.dev with:

- **Subject**: "Security Vulnerability in LoadTest"
- **Description**: A detailed description of the vulnerability
- **Impact**: What could an attacker accomplish?
- **Reproduction**: Steps to reproduce the issue
- **Environment**: Version, Python version, OS, etc.
- **Possible fix**: If you have suggestions for fixing the issue

### 3. What to Expect

- **Initial Response**: Within 48 hours, we will acknowledge receipt of your report
- **Investigation**: We will investigate and validate the vulnerability
- **Updates**: We will provide updates on our progress every 5 business days
- **Resolution**: Once fixed, we will release a security patch and credit you (if desired)

### 4. Disclosure Timeline

We follow a coordinated disclosure process:

1. **Day 0**: Vulnerability reported
2. **Day 2**: Acknowledgment sent
3. **Day 30**: Target date for fix (may vary by severity)
4. **Day 45**: Public disclosure after fix is released

We may adjust this timeline based on severity and complexity.

## Security Best Practices

### For Users

1. **Keep Updated**: Always use the latest version of LoadTest
2. **Validate Targets**: Ensure you're only testing systems you own or have permission to test
3. **Rate Limiting**: Use appropriate rate limits to avoid overwhelming target systems
4. **Data Protection**: Securely store any test data or reports
5. **Network Security**: Run tests from secure network environments

### For Developers

1. **Dependency Management**: Keep all dependencies updated
2. **Code Review**: All security-related code must be reviewed
3. **Testing**: Include security tests in your test suite
4. **Documentation**: Document security considerations
5. **Least Privilege**: Use minimal necessary permissions

## Security Considerations for Load Testing

### Responsible Testing

LoadTest is a powerful tool that can generate significant traffic. Please use responsibly:

- **Authorization**: Only test systems you own or have explicit written permission to test
- **Impact Assessment**: Consider the impact on production systems
- **Rate Limits**: Start low and increase gradually
- **Time Windows**: Test during appropriate maintenance windows
- **Monitoring**: Monitor target system health during tests

### Data Security

When using LoadTest with real data:

- **Data Sanitization**: Never use real user credentials in tests
- **Log Security**: Secure access to test logs and reports
- **Data Retention**: Define retention policies for test data
- **Encryption**: Use encryption for sensitive test configurations

## Security Features

LoadTest includes several security-focused features:

### Safe Defaults

- Conservative default rate limits
- Built-in timeout handling
- Connection pooling with limits
- Automatic resource cleanup

### Request Safety

- Configurable timeouts
- Connection reuse
- SSL/TLS verification
- Request size limits

## Known Security Considerations

### Denial of Service Risk

LoadTest can generate high volumes of traffic. Be aware that:

- Misuse could impact target systems
- Always have authorization before testing
- Monitor target system health
- Have abort mechanisms ready

### Data Exposure in Reports

Test reports may contain:

- URLs and endpoints tested
- Response data samples
- Error messages

Review reports before sharing.

### Network Security

When running distributed tests:

- Use secure communication channels
- Authenticate test nodes
- Encrypt sensitive configuration data
- Validate test script sources

## Security Testing

Our security testing includes:

- Static analysis with Bandit
- Dependency vulnerability scanning
- Regular security audits
- Input validation testing

## Responsible Disclosure

We follow responsible disclosure practices:

1. Security issues are handled privately
2. Fixes are prepared before public disclosure
3. Reporters are credited (unless they prefer anonymity)
4. CVEs are obtained for significant vulnerabilities

## Compliance Notes

When using LoadTest:

- Ensure compliance with your organization's security policies
- Follow applicable laws and regulations
- Obtain proper authorization
- Document testing activities

## Credits

We thank the following security researchers who have responsibly disclosed vulnerabilities:

- [Your name could be here!]

## Contact

- **Security Team**: security@loadtest.dev
- **General Inquiries**: contact@loadtest.dev
- **PGP Key**: [Available upon request]

---

Last Updated: 2024
