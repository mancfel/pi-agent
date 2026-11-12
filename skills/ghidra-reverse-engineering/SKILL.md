---
name: ghidra-reverse-engineering
description: Orchestrates systematic reverse engineering of arbitrary binaries (.dll, .exe, custom formats) using Ghidra MCP integration and Python automation; covers PE analysis, compression codec discovery, binary format mapping, entropy classification, API trace parsing, and extraction pipeline development.
---

# Ghidra Reverse Engineering — Binary Analysis Framework

## Description

Orchestrates systematic reverse engineering of arbitrary binaries (`.dll`, `.exe`, custom formats) using Ghidra, MCP integration, and Python automation. Covers PE analysis, compression codec discovery, binary format mapping, and data extraction pipeline development.

**Applicable to**: Any Windows executable or proprietary file format requiring static/dynamic analysis for format documentation or tool development.

---

## Workflow Overview

```
DISCOVER → ANALYZE → DECOMPILE → MAP → VALIDATE
   ↓          ↓           ↓         ↓        ↓
  Scan      Static       Dynamic    Cross-  Script
  Headers   Analysis     Debugging  Refs    Validation
```

### Phases

| Phase | Goal | Tools | Output |
|-------|------|-------|--------|
| **0. Discovery** | Identify file type, packing, entry points | Ghidra import wizard, PE analyzer | Binary classification report |
| **1. Static Analysis** | Map functions, strings, imports/exports | Ghidra decompiler, symbol table | Function call graph + string database |
| **2. Dynamic Analysis** | Trace execution flow, capture runtime state | API Monitor, ETW tracing, ProcMon | Runtime parameter dump |
| **3. Cross-Reference Mapping** | Link binary logic to data formats | XREF analysis, Python scripts | Format hypothesis document |
| **4. Validation** | Test hypotheses against real data files | Custom extraction scripts | Success/failure metrics |

---

## Phase 0 — Binary Discovery & Classification

### Step 1: Identify File Type and Packing Layer

```python
# Quick check for PE header and common packers
import struct

with open('binary.dll', 'rb') as f:
    mz = f.read(2)
    if mz != b'MZ':
        print("NOT a PE file")
    
    f.seek(0x3C)
    pe_offset = struct.unpack('<I', f.read(4))[0]
    f.seek(pe_offset)
    pe_sig = f.read(4)
    
    if pe_sig == b'PE\x00\x00':
        print("Valid PE file")
        
        # Check for packer signatures in entire binary
        full_data = open('binary.dll','rb').read()
        known_packers = ['UPX', 'ASPack', 'Themida', 'VMProtect', 'Enigma']
        for marker in known_packers:
            if marker.encode() in full_data:
                print(f"WARNING: Possible {marker} packing detected!")
```

### Step 2: Import into Ghidra via MCP Bridge

**Prerequisites**:
- Ghidra installed (e.g., `C:\Tools\Ghidra\`) with JDK 17+ or 25+
- `ghidramcp.exe` bridge running on configured port (default 8089)
- Program loaded in Ghidra headless mode or through script console

```bash
# Start Ghidra server (headless, no GUI needed for analysis)
cd C:\Tools\Ghidra\support
JavaSupport\Util\java.exe -jar ghidraServer.jar --no-browser

# Or use script console for batch analysis
python scripts/analyze_pe_header.py path\\to\\binary.dll
```

---

## Phase 1 — Static Analysis Strategy

### A. Entry Point Tracing

Every PE has an entry point. For DLLs, trace through `DllMain`:

```python
# In Ghidra Script Console (Python)
from ghidra.app.decompiler import DecompInterface

decomp = DecompInterface()
decomp.openProgram(currentProgram)

entry = currentProgram.getEntryPoint()
print(f"Entry point: {entry}")

func = getFunctionAt(entry)
if func:
    print(f"Entry function: {func.getName()}")
    decomp.decompileFunction(func, 30, None)
    print(decomp.getDecompiledFunction().getDecompilerXML())
```

**What to look for at entry**:
1. `LoadLibrary` / `GetProcAddress` calls → API hashing or dynamic loading
2. `VirtualAlloc` + `VirtualProtect` → Code injection or unpacking stub
3. `CreateThread` → Multi-threaded initialization (common in game engines)
4. XOR/ROT loops over code sections → Simple obfuscation layer

### B. String Analysis — Finding Format Signatures and Paths

Ghidra's string finder is critical for discovering:

| Pattern | What It Reveals | Example Use Case |
|---------|-----------------|------------------|
| File extensions (`.dat`, `.bin`, etc.) | Archive/file formats used by the binary | `"package.dat"`, `"config.json"` |
| Compression constants | Codec identification strings | `"DEFLATE"`, `"LZMA"`, `"ZSTD"` |
| Error messages | Function purpose hints | `"Failed to decompress tile"` or `"Invalid checksum"` |
| Hash function names | Data indexing scheme | `"Murmur3"`, `"CityHash"`, `"CRC32"` |

**Script**: Extract and categorize all strings by type:

```python
from ghidra.program.model.symbol import SourceType

strings = currentProgram.getListing().getCodeBlocks(None)
for cblock in currentProgram.getMemory().getBlocksWithName("Strings"):
    mem = currentProgram.getMemory()
    for addr in mem.getBlock("Strings").getAddresses(True):
        try:
            s = getString(addr)
            if s and len(s) > 4:
                print(f"{addr}: {s}")
        except:
            pass
```

### C. Function Signature Recovery

Ghidra can often auto-detect function signatures from calling conventions. Override ambiguous ones manually:

```python
# Force signature on suspected codec factory or dispatcher function
from ghidra.program.model.listing import FunctionSignature

sig = makeFunction(0xADDRESS, "CustomCodecFactory")
setFunctionSignature(sig, 
    "char param_1, uint param_2, longlong *param_3, undefined8 **param_4")
```

**Key functions to identify in any compression/codec DLL**:

| Pattern | Purpose | What It Does |
|---------|---------|--------------|
| `Create*` / `Init*` | Factory/costructor entry point | Allocates and initializes codec object |
| `GetFactory*` | Interface retrieval | Returns COM-style or vtable interface pointer |
| Format dispatcher (enum switch) | Routes format → internal code | Maps user-facing enum values to implementation-specific codes |
| Core worker function (~5-10KB size) | Actual decompression/compression logic | Tile-based parallel processing, GPU/CPU fallback paths |

---

## Phase 2 — Dynamic Analysis & Runtime Capture

### A. API Monitor Setup for Custom Storage APIs

**Problem**: Standard ProcMon filters may show nothing if the binary uses kernel-mode storage providers that bypass `CreateFile`/`ReadFile`.

**Solution**: Use **API Monitor** with categories enabled based on what you're tracking:

| Category | What It Captures | Performance Impact |
|----------|-----------------|-------------------|
| Data and Storage | Custom storage APIs, IRP traces | Low-Medium |
| DirectX (if graphics-related) | Resource creation, staging buffers | Medium |
| Memory Management | VirtualAlloc/VirtualFree for buffers | Low |
| Threads/Sync | Thread pool workers for parallel processing | Low |

**Capture duration**: Minimum 20 minutes in scenarios where multiple archives/files stream simultaneously.

### B. ETW Event Tracing (Kernel-Level Alternative)

Built into Windows — no third-party tools needed:

```cmd
REM Run as Administrator BEFORE starting target application
logman create trace "CustomTrace" -p {GUID-HERE} -o C:\temp\trace.etl -ets

# Run target workload for required duration
# Then stop tracing and convert to readable format
logman stop "CustomTrace"
tracerpt.exe C:\temp\trace.etl -o C:\temp\report.csv -ct CSV
```

**Finding the correct GUID**: Search Microsoft documentation or use `logman query providers` to list available event providers.

### C. Parsing API Monitor Captures (.apmx64 format)

Extracted captures typically live in a structured folder hierarchy under `data/`. Use provided scripts:

| Script | Purpose | Key Output |
|--------|---------|------------|
| `parse_apmx_*.py` | Extract function call parameters | funcID, module base address, timestamps |
| `extract_*_calls.py` | Filter calls by target module | Parameter dump of specific functions |
| `analyze_*_funcids.py` | Count function IDs per module | Top funcIDs across all modules |

**Binary record layout (typical API Monitor format)**:
```
+0x00: u8[4]   flags  
+0x04: u32     param_type (usually 3 for normal calls)
+0x08: u32     sequential call index
+0x0C: u32     parent call ID
+0x10: u32     funcID (internal identifier for the API)
+0x30: u64     calling module base address
+0x40: u64     return address
+0x48: u64     FILETIME timestamp
```

---

## Phase 3 — Cross-Reference Mapping

### A. Linking Binary Logic to Data Formats

Once you've identified codec or processing functions in Ghidra, map them back to data file structures using this workflow:

**Step 1**: Identify the core processing entry point (e.g., `FUN_XXXXX`)

**Step 2**: Trace backwards through callers to find where data pointers originate:
```python
# In Ghidra Script Console - find all references TO a target function
funcs = currentProgram.getFunctionManager().getFunctions(True)
target_addr = toAddr("0xADDRESS")

for func in funcs:
    refs = getReferencesTo(func.getStartAddress())
    for ref in refs:
        print(f"Called from {ref.getSourcePath()} @ {ref.getAddress()}: {ref}")
```

**Step 3**: Identify how the application structures chunks before passing them to processing APIs. Look for:
- Metadata headers (per-chunk size/count information)
- Global chunk headers (uncompressed size, tile count, compression type enum)
- Delimiter bytes used as record separators between data blocks

### B. Index/Database → Data Offset Mapping

Many proprietary formats use an index section containing entries with hash values and offsets:

```c++
// Typical index entry structure (inferred pattern):
struct IndexEntry {
    uint32_t hash_32bit;        // Hash of asset path or identifier  
    uint32_t internal_id_or_ptr;// Varies widely depending on format
    char name[4..64];           // ASCII filename or resource ID string
    uint32_t field_after_name1; // Large values, possibly cross-archive offsets
    uint32_t field_after_name2; // Also large/variable
};
```

**Cross-reference strategy**:
1. Extract all entries from the index using a Python parser script
2. Search for corresponding strings in Ghidra's string database (e.g., `"assetname"`)
3. Trace backwards from each string reference to find hash computation logic
4. Map computed hashes → Locator records → actual file byte offsets

---

## Phase 4 — Validation & Script Development

### A. Testing Decompression Hypotheses

Use these scripts to validate format assumptions against real data files:

| Script | What It Tests | Input File | Output |
|--------|---------------|------------|--------|
| `scan_compression_magic.py` | Magic bytes at arbitrary offsets | Any proprietary `.dat/.bin/core` file | List of magic occurrences + surrounding context |
| `analyze_chunk_headers.py` | Chunk framing structure around magic bytes | First few MB of data file | Header layout with field breakdowns |
| `test_mixed_decompress.py` | Multiple decompression methods (Deflate/LZMA/GZIP/ZSTD) | Offset ranges from magic scan | Success/failure counts per codec |
| `calculate_offset_mapping.py` | Index/table cumulative offset calculation | Data file header + index section | Expected vs actual byte positions |

### B. Entropy Analysis for Data Region Classification

High entropy = compressed/encrypted data; low entropy = metadata/padding:

```python
import math, os

def calculate_entropy(data):
    """Calculate Shannon entropy of a byte sequence."""
    if not data: return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    
    entropy = 0.0
    length = len(data)
    for count in freq:
        if count == 0: continue
        p = count / length
        entropy -= p * math.log2(p)
    
    return entropy

# Scan first N MB of file in configurable chunk sizes
with open('data_file.bin', 'rb') as f:
    chunk_size = 0x10000  # 64KB chunks
    offset = 0
    
    while offset < max_target and not f.seek(offset, 0):
        data = f.read(chunk_size)
        if len(data) != chunk_size: break
        
        ent = calculate_entropy(data)
        
        label = "LOW" if ent < 3 else ("MED" if ent < 6 else "HIGH")
        print(f"@{offset:#010X} | Entropy={ent:.2f}/{8.0} [{label}]")
        
        # Classify regions based on entropy thresholds
        if ent > 7.0:
            print("  → Likely compressed/encrypted asset data")
        elif ent < 4.0:
            print("  → Likely metadata, padding, or sparse allocation")
            
        offset += chunk_size
```

### C. Building the Extraction Pipeline

Once all format pieces are understood, combine them into a unified extraction tool:

**Pipeline stages**:

```
1. Parse file header (magic + version + entry table) 
   ↓
2. Resolve index entries to file byte offsets
   ↓  
3. For each resource path in locator/database:
   - Compute hash of path using identified algorithm
   - Look up hash in index/entry table
   - Get tile/chunk ID from relevant field
   - Calculate physical byte offset using cumulative sizes
4. Read compressed chunk at calculated offset
5. Determine codec type from enum field or magic bytes
6. Decompress: Tile unpacking → raw asset data
7. Write extracted files with correct extensions (.fbx, .dds, etc.)
```

**Codec routing logic pattern**:

```python
def decompress_chunk(compressed_data, format_enum, uncompressed_size):
    """Route to appropriate decompressor based on format enum."""
    
    if format_enum == -1:  # RAW / UNCOMPRESSED
        return compressed_data[:uncompressed_size]
        
    elif format_enum == 0:  # NONE specified but compression expected
        raise ValueError("Uncompressed chunk requested but compression specified")
        
    elif format_enum == 1:  # GDeflate or similar tile-based codec
        # Tile-based parallel processing (e.g., ~64KB/tile)
        tile_count = (len(compressed_data) + 0xFFFF) >> 16
        
        results = []
        for i in range(tile_count):
            start = i * 0x10000
            end = min(start + 0x10000, len(compressed_data))
            tile_data = compressed_data[start:end]
            
            # GPU path preferred; fallback to CPU Thread Pool
            try:
                result = custom_gpu_decompress(tile_data)
            except:
                result = zlib.decompress(tile_data, -zlib.MAX_WBITS)
                
            results.append(result)
        
        return b''.join(results)[:uncompressed_size]
    
    elif format_enum == 2:  # LZMA (inferred from magic bytes)
        import lzma
        return lzma.decompress(compressed_data)
    
    else:
        raise ValueError(f"Unknown compression format: {format_enum}")
```

---

## Common Pitfalls & Solutions

| Problem | Cause | Solution |
|---------|-------|----------|
| Ghidra hangs on full analysis of large DLL/EXE | Binary is encrypted/packed; PE header misleading | Skip "Run Full Analysis"; use "Extract Strings" only initially |
| Zero calls to target module in API Monitor capture | Target uses kernel-mode drivers bypassing user hooks | Use ETW tracing or extend workload session duration significantly |
| Decompression fails despite valid magic bytes | Unknown framing layer before actual compressed stream | Analyze chunk headers at offsets found by magic scan script; look for hash/checksum fields preceding magic |
| Index hashes don't match locator database values | Hash computation may include path prefix, case folding, or custom seed | Trace hash function in Ghidra decompiler output; compare against known implementations (Murmur3, CRC32, etc.) |
| Slow performance with large data files (>1GB) | Python reads entire file into memory | Use memory-mapped files (`mmap`) or read-only sequential scanning |

---

## Quick Reference — Analysis Checklist

### DLLs and Executables to Import

| Priority | File Type | Purpose |
|----------|-----------|---------|
| 1 | Main engine/game DLL | Core logic, compression codecs, asset loaders |
| 2 | Storage/codec-specific DLL | DirectStorage, Oodle, custom decompression libraries |
| 3 | Main executable (.exe) | Entry points, initialization routines |

### Data Archives to Analyze

| Archive Type | Typical Size Range | Contents |
|--------------|-------------------|----------|
| Primary archive (`.core`, `.pak`, `.dat`) | ~500MB - 2GB | Sample with thousands of filenames/resources |
| Secondary archives | Up to several GB each | Various asset packs (terrain, models, textures, audio) |
| Stream files (~10-100+) | 1.5–5GB each | Large continuous data streams |

### Key Functions to Identify in Codec DLLs

| Address Pattern | Function Role | What to Extract |
|-----------------|---------------|-----------------|
| `Create*` / `Init*` at low addresses | Factory/costructor entry point | Parameter layout, magic value validation |
| `GetFactory*` | Interface retrieval | COM interface GUIDs or vtable structure |
| Format dispatcher (enum switch ~mid-range) | Routes format → internal code | Enum-to-code mapping table |
| Core worker function (~5-20KB size) | Actual decompression/compression logic | Tile count calculation, GPU/CPU fallback paths, error codes |

---

## Output Artifacts

All analysis results should be stored in:

- **`Raw/` folder**: Raw evidence (web pages, hex dumps, protocol notes, screenshots, Ghidra decompilation outputs)
- **`index.md`** at project root: Living summary of findings, open points, hypothesis status (`proven/disproven/pending`)
- **`scripts/` folder**: Generic, reusable Python scripts for format analysis and extraction testing
- **Final tool**: Complete asset/data extraction pipeline producing usable files for target applications (Blender, Unreal Engine, etc.)

---

## Exit Criterion

The investigation is complete only when a full data pipeline works end-to-end — from raw proprietary file data through extraction to importable/useable files in target applications. No partial findings count as done.
