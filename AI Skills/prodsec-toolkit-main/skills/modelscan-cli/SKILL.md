---
name: modelscan-cli
description: Scan ML/AI models for malicious code and serialization attacks using ModelScan. This skill should be used when users want to scan machine learning model files (PyTorch, TensorFlow, Keras, Pickle, etc.) for security vulnerabilities, unsafe operators, or code injection attacks.
metadata:
  version: 1.0.0
  category: code-analysis
  tags: security, ai-ml, model-scanning, serialization-attacks
  status: active
---

# ModelScan CLI

This skill provides guidance for scanning machine learning model files for malicious code using [ModelScan](https://github.com/protectai/modelscan) by Protect AI.

## About ModelScan

ModelScan detects **Model Serialization Attacks** - where malicious code is embedded in model files during the save process. When a model is loaded (e.g., `torch.load(PATH)`), the malicious code executes immediately. These attacks can lead to:

- Credential theft (cloud credentials, API keys)
- Data theft (inference requests)
- Data/model poisoning
- Arbitrary code execution

ModelScan reads model files byte-by-byte looking for dangerous code signatures without executing them, making it fast and safe.

## Supported Formats

| ML Library | Serialization Format | Extensions |
|------------|---------------------|------------|
| PyTorch | Pickle | `.bin`, `.pt`, `.pth`, `.ckpt` |
| TensorFlow | Protocol Buffer | `.pb` |
| Keras | H5/HD5 | `.h5` |
| Keras V3 | Keras format | `.keras` |
| NumPy | NumPy format | `.npy` |
| Sklearn, XGBoost, etc. | Pickle variants | `.pkl`, `.pickle`, `.joblib`, `.dill`, `.dat`, `.data` |
| Archives | ZIP | `.zip`, `.npz` |

## CLI Usage

### Basic Scan

```bash
modelscan -p /path/to/model_file.pkl
```

### Scan with Output Options

```bash
# JSON output to file
modelscan -p /path/to/model -r json -o scan_results.json

# Console output (default)
modelscan -p /path/to/model -r console

# Show skipped files
modelscan -p /path/to/model --show-skipped
```

### Log Levels

```bash
modelscan -p /path/to/model -l DEBUG    # CRITICAL, ERROR, WARNING, INFO, DEBUG
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Scan completed, no vulnerabilities found |
| 1 | Scan completed, vulnerabilities found |
| 2 | Scan failed (modelscan error) |
| 3 | No supported files found |
| 4 | Usage error (invalid options) |

## Severity Levels

### CRITICAL
Unsafe operators that can execute arbitrary code:
- `exec`, `eval`, `compile`, `getattr`, `apply`, `open`, `breakpoint`, `__import__`
- Full modules: `runpy`, `os`, `nt`, `posix`, `socket`, `subprocess`, `sys`, `pty`, `pickle`, `_pickle`, `bdb`, `pdb`, `shutil`, `asyncio`
- `operator.attrgetter` (code execution vector)

### HIGH
Unsafe operators that can't execute code directly but enable exploitation:
- `webbrowser.open()`
- `httplib`, `http.client.HTTPSConnection()`
- `requests.api`, `aiohttp.client`
- TensorFlow `ReadFile`, `WriteFile` operators

### MEDIUM
- Unknown operators not supported by parent ML library
- Keras Lambda layers (can be exploited for code injection)
- Custom operators

### LOW
Currently unused.

## Common Scanning Workflows

### Pre-training Scan
Scan downloaded/pre-trained models before loading:
```bash
modelscan -p ./downloaded_model.pt
```

### Post-training Scan
Scan models after training to detect supply chain attacks:
```bash
modelscan -p ./trained_model/ -r json -o post_training_scan.json
```

### Pre-deployment Scan
Scan before deploying to endpoints:
```bash
modelscan -p ./production_model.pkl --show-skipped
```

### Batch Scanning
Scan entire model directories:
```bash
modelscan -p ./models/ -r json -o scan_results.json
```

## Programmatic Usage (Python)

```python
from modelscan.modelscan import ModelScan
from modelscan.settings import DEFAULT_SETTINGS

# Initialize scanner
scanner = ModelScan(settings=DEFAULT_SETTINGS)

# Scan model
results = scanner.scan("/path/to/model.pkl")

# Check for issues
if scanner.issues.all_issues:
    issues_by_severity = scanner.issues.group_by_severity()
    for severity, issues in issues_by_severity.items():
        print(f"{severity}: {len(issues)} issues")

# Generate report
scanner.generate_report()
```

## CI/CD Integration

For pipeline integration, use JSON output and check exit codes:

```bash
#!/bin/bash
modelscan -p ./model.pkl -r json -o scan.json
exit_code=$?

if [ $exit_code -eq 1 ]; then
    echo "Vulnerabilities found! Check scan.json"
    exit 1
elif [ $exit_code -gt 1 ]; then
    echo "Scan failed with error code $exit_code"
    exit 1
fi

echo "Model scan passed"
```
