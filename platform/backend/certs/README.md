# SSL Certificates for Database Connections

This directory contains CA certificates for secure database connections.

## Supabase CA Certificate

To enable proper SSL verification with Supabase's connection pooler:

### Option 1: Download from Dashboard (Recommended)

1. Log into [Supabase Dashboard](https://supabase.com/dashboard)
2. Go to your project's **Database Settings**
3. Find **SSL Configuration** section
4. Click **Download Certificate**
5. Save the file as `supabase-ca.crt` in this directory

### Option 2: Environment Variable

Set the `SUPABASE_CA_CERT` environment variable with either:
- The raw PEM certificate content
- Base64-encoded certificate content

Example (Railway):
```bash
railway variables set SUPABASE_CA_CERT="$(cat supabase-ca.crt | base64)"
```

## Why This Matters

Without the CA certificate, connections to Supabase's pooler will either:
- **Fail** with `ssl.SSLCertVerificationError: self-signed certificate in certificate chain`
- **Use insecure fallback** (disabled verification) with a warning in logs

The proper fix is to configure the CA certificate so SSL verification works correctly.

## Verification

When properly configured, you'll see this in logs:
```
SSL: Using CA certificate from SUPABASE_CA_CERT env var
```
or
```
SSL: Using bundled CA certificate from .../certs/supabase-ca.crt
```

If you see this warning, the certificate is not configured:
```
SSL: No CA certificate configured for Supabase. Disabling certificate verification.
```

## References

- [Supabase SSL Enforcement Docs](https://supabase.com/docs/guides/platform/ssl-enforcement)
- [GitHub Issue #17971](https://github.com/supabase/supabase/issues/17971) - Self-signed certificate error
