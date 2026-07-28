# Security policy

This repository accompanies a published research chapter. It is research code, not a product,
and no production deployment is intended or supported.

## Reporting

If you find a reproducibility problem — a script that fails, an output that does not match the
chapter, or a documentation error — please open an issue, or contact the corresponding author
at lohithsaiandra18@gmail.com.

## Scope

Security vulnerabilities unrelated to reproducibility are outside the scope of this repository.
The code reads local files, trains models in memory and writes results to disk. It opens no
network connections, requires no credentials, and processes no personal data: the datasets are
synthetic and contain no individual mobility records.

## Supported version

Only the released version, v1.0.0, corresponds to the published chapter. Later versions, if
any, may diverge from the published results and will be documented in `CHANGELOG.md`.
